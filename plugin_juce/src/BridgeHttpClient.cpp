#include "BridgeHttpClient.h"

namespace suno::bridge
{
namespace
{
juce::String makeRequestId()
{
    return juce::Uuid().toString();
}

juce::String sha256Hex(const juce::String& input)
{
    juce::SHA256 digest(input.toRawUTF8(), static_cast<size_t>(input.getNumBytesAsUTF8()));
    return digest.toHexString();
}

JobSummary parseJob(const juce::var& jobVar)
{
    JobSummary summary;
    if (! jobVar.isObject())
        return summary;

    auto* obj = jobVar.getDynamicObject();
    summary.id = obj->getProperty("id").toString();
    summary.type = obj->getProperty("type").toString();
    summary.status = obj->getProperty("status").toString();
    summary.remoteJobId = obj->getProperty("remoteJobId").toString();
    summary.progress = static_cast<float>(obj->getProperty("progress"));
    summary.lastError = obj->getProperty("lastError").toString();

    if (auto outputAssets = obj->getProperty("outputAssets"); outputAssets.isArray())
        for (const auto& asset : *outputAssets.getArray())
            summary.outputAssets.add(asset.toString());

    return summary;
}
}

BridgeHttpClient::BridgeHttpClient(DiscoveryInfo discovered, ClientConfig clientConfig)
    : discovery(std::move(discovered)), config(std::move(clientConfig))
{
}

bool BridgeHttpClient::handshake(juce::String& errorOut)
{
    juce::var response;
    if (! executeJson("GET", "/capabilities", {}, response, errorOut))
        return false;

    if (! response.isObject())
    {
        errorOut = "Invalid capabilities response";
        return false;
    }

    return true;
}

bool BridgeHttpClient::createTextJob(const juce::String& prompt,
                                     const juce::var& metadata,
                                     JobSummary& outJob,
                                     juce::String& errorOut)
{
    juce::DynamicObject payload;
    payload.setProperty("clientRequestId", makeRequestId());
    payload.setProperty("prompt", prompt);
    payload.setProperty("metadata", metadata);

    juce::var response;
    if (! executeJson("POST", "/jobs/text", juce::JSON::toString(&payload), response, errorOut))
        return false;

    auto* obj = response.getDynamicObject();
    outJob = parseJob(obj->getProperty("job"));
    return ! outJob.id.isEmpty();
}

bool BridgeHttpClient::importAsset(const juce::File& source,
                                   juce::String& outAssetId,
                                   juce::String& errorOut)
{
    if (! source.existsAsFile())
    {
        errorOut = "Asset source file not found";
        return false;
    }

    // Thin scaffold: uses JSON stub rather than full multipart encoder in this milestone.
    // TODO: replace with binary multipart writer for production.
    juce::DynamicObject payload;
    payload.setProperty("filePath", source.getFullPathName());

    juce::var response;
    if (! executeJson("POST", "/assets/import", juce::JSON::toString(&payload), response, errorOut))
        return false;

    outAssetId = response.getProperty("assetId", {}).toString();
    return outAssetId.isNotEmpty();
}

bool BridgeHttpClient::createAudioJob(const juce::String& assetId,
                                      const juce::String& prompt,
                                      const juce::var& metadata,
                                      JobSummary& outJob,
                                      juce::String& errorOut)
{
    juce::DynamicObject payload;
    payload.setProperty("clientRequestId", makeRequestId());
    payload.setProperty("prompt", prompt);
    payload.setProperty("metadata", metadata);
    payload.setProperty("assetId", assetId);

    juce::var response;
    if (! executeJson("POST", "/jobs/audio", juce::JSON::toString(&payload), response, errorOut))
        return false;

    auto* obj = response.getDynamicObject();
    outJob = parseJob(obj->getProperty("job"));
    return ! outJob.id.isEmpty();
}

bool BridgeHttpClient::getJob(const juce::String& jobId,
                              JobSummary& outJob,
                              juce::String& errorOut)
{
    juce::var response;
    if (! executeJson("GET", "/jobs/" + jobId, {}, response, errorOut))
        return false;

    outJob = parseJob(response);
    return ! outJob.id.isEmpty();
}

bool BridgeHttpClient::cancelJob(const juce::String& jobId,
                                 JobSummary& outJob,
                                 juce::String& errorOut)
{
    juce::var response;
    if (! executeJson("POST", "/jobs/" + jobId + "/cancel", "{}", response, errorOut))
        return false;

    outJob = parseJob(response);
    return ! outJob.id.isEmpty();
}

juce::String BridgeHttpClient::buildBaseUrl() const
{
    return "http://" + discovery.host + ":" + juce::String(discovery.port);
}

bool BridgeHttpClient::executeJson(const juce::String& method,
                                   const juce::String& path,
                                   const juce::String& body,
                                   juce::var& response,
                                   juce::String& errorOut)
{
    juce::StringArray headers;
    const auto requestId = makeRequestId();
    const auto nonce = makeRequestId();
    const auto timestamp = juce::String(static_cast<int64>(juce::Time::getCurrentTime().toMilliseconds() / 1000));
    const auto bodyHash = sha256Hex(body);
    const auto signaturePayload = timestamp + "." + nonce + "." + bodyHash;
    const auto signature = sha256Hex(config.sharedSecret + "." + signaturePayload);

    headers.add("X-Plugin-Version: " + config.pluginVersion);
    headers.add("X-Protocol-Version: " + config.protocolVersion);
    headers.add("X-Request-ID: " + requestId);
    headers.add("X-Signature-Timestamp: " + timestamp);
    headers.add("X-Signature-Nonce: " + nonce);
    headers.add("X-Body-Sha256: " + bodyHash);
    headers.add("X-Signature: " + signature);
    headers.add("Content-Type: application/json");

    auto endpoint = juce::URL(buildBaseUrl() + path);
    auto stream = endpoint.createInputStream(
        juce::URL::InputStreamOptions(juce::URL::ParameterHandling::inAddress)
            .withExtraHeaders(headers.joinIntoString("\n"))
            .withHttpRequestCmd(method)
            .withConnectionTimeoutMs(6000)
            .withStatusCode(nullptr)
            .withResponseHeaders(nullptr)
            .withNumRedirectsToFollow(2)
            .withPOSTData(body.toRawUTF8(), body.getNumBytesAsUTF8()));

    if (stream == nullptr)
    {
        errorOut = "Bridge request failed: could not open stream";
        return false;
    }

    const auto raw = stream->readEntireStreamAsString();
    response = juce::JSON::parse(raw);
    if (response.isVoid())
    {
        errorOut = "Bridge response parse error";
        return false;
    }

    return true;
}
} // namespace suno::bridge
