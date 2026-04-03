#include "BridgeHttpClient.h"

namespace suno::bridge
{
namespace
{
juce::String makeRequestId()
{
    return juce::Uuid().toString();
}

juce::String sha256Hex(const void* data, size_t size)
{
    juce::SHA256 digest(data, size);
    return digest.toHexString();
}

juce::MemoryBlock sha256Raw(const void* data, size_t size)
{
    juce::SHA256 digest(data, size);
    juce::MemoryBlock out;
    out.append(digest.getRawData(), 32);
    return out;
}

juce::String hmacSha256Hex(const juce::String& key, const juce::String& message)
{
    constexpr size_t blockSize = 64;

    juce::MemoryBlock keyBlock;
    keyBlock.append(key.toRawUTF8(), static_cast<size_t>(key.getNumBytesAsUTF8()));
    if (keyBlock.getSize() > blockSize)
        keyBlock = sha256Raw(keyBlock.getData(), keyBlock.getSize());
    if (keyBlock.getSize() < blockSize)
        keyBlock.append(juce::String::repeatedString("\0", static_cast<int>(blockSize - keyBlock.getSize())).toRawUTF8(),
                        blockSize - keyBlock.getSize());

    juce::MemoryBlock oKeyPad, iKeyPad;
    oKeyPad.setSize(blockSize);
    iKeyPad.setSize(blockSize);

    auto* keyBytes = static_cast<const uint8_t*>(keyBlock.getData());
    auto* oBytes = static_cast<uint8_t*>(oKeyPad.getData());
    auto* iBytes = static_cast<uint8_t*>(iKeyPad.getData());
    for (size_t i = 0; i < blockSize; ++i)
    {
        oBytes[i] = static_cast<uint8_t>(keyBytes[i] ^ 0x5c);
        iBytes[i] = static_cast<uint8_t>(keyBytes[i] ^ 0x36);
    }

    juce::MemoryBlock inner;
    inner.append(iKeyPad.getData(), iKeyPad.getSize());
    inner.append(message.toRawUTF8(), static_cast<size_t>(message.getNumBytesAsUTF8()));
    auto innerHash = sha256Raw(inner.getData(), inner.getSize());

    juce::MemoryBlock outer;
    outer.append(oKeyPad.getData(), oKeyPad.getSize());
    outer.append(innerHash.getData(), innerHash.getSize());
    return sha256Hex(outer.getData(), outer.getSize());
}

juce::String quote(const juce::String& value)
{
    return "\"" + value.replace("\"", "\\\"") + "\"";
}

juce::MemoryBlock buildMultipartBody(const juce::String& boundary,
                                     const juce::StringPairArray& fields,
                                     const juce::String& fileField,
                                     const juce::File* file,
                                     const juce::String& mimeType)
{
    juce::MemoryBlock body;
    auto appendString = [&body](const juce::String& s)
    {
        body.append(s.toRawUTF8(), static_cast<size_t>(s.getNumBytesAsUTF8()));
    };

    for (int i = 0; i < fields.size(); ++i)
    {
        appendString("--" + boundary + "\r\n");
        appendString("Content-Disposition: form-data; name=" + quote(fields.getAllKeys()[i]) + "\r\n\r\n");
        appendString(fields.getAllValues()[i] + "\r\n");
    }

    if (file != nullptr)
    {
        appendString("--" + boundary + "\r\n");
        appendString("Content-Disposition: form-data; name=" + quote(fileField) + "; filename=" + quote(file->getFileName()) + "\r\n");
        appendString("Content-Type: " + mimeType + "\r\n\r\n");
        body.append(file->loadFileAsData().getData(), file->loadFileAsData().getSize());
        appendString("\r\n");
    }

    appendString("--" + boundary + "--\r\n");
    return body;
}
}

BridgeHttpClient::BridgeHttpClient(DiscoveryInfo discovered, ClientConfig clientConfig)
    : discovery(std::move(discovered)), config(std::move(clientConfig))
{
}

bool BridgeHttpClient::handshake(juce::String& errorOut)
{
    HttpResponse response;
    if (! executeJson("GET", "/capabilities", "", response, errorOut))
        return false;

    if (response.statusCode < 200 || response.statusCode >= 300)
        return parseErrorPayload(response.payload, errorOut);

    auto protocol = response.payload.getProperty("protocol", juce::var());
    if (! protocol.isObject())
    {
        errorOut = "Capabilities missing protocol range";
        return false;
    }

    const auto minSupported = protocol.getProperty("min_supported", juce::var()).toString();
    const auto maxSupported = protocol.getProperty("max_supported", juce::var()).toString();
    if (minSupported.isEmpty() || maxSupported.isEmpty())
    {
        errorOut = "Capabilities missing min/max protocol";
        return false;
    }

    // Lightweight range check: same major and bounded lexical compare for this scaffold.
    if (config.protocolVersion < minSupported || config.protocolVersion > maxSupported)
    {
        errorOut = "Protocol version out of supported range: " + minSupported + "-" + maxSupported;
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

    HttpResponse response;
    if (! executeJson("POST", "/jobs/text", juce::JSON::toString(&payload), response, errorOut))
        return false;

    if (response.statusCode < 200 || response.statusCode >= 300)
        return parseErrorPayload(response.payload, errorOut);

    return parseJobFromPayload(response.payload.getProperty("job", juce::var()), outJob, errorOut);
}

bool BridgeHttpClient::importAsset(const juce::File& source,
                                   bool normalizeOnImport,
                                   juce::String& outAssetId,
                                   juce::String& errorOut)
{
    if (! source.existsAsFile())
    {
        errorOut = "Asset source file not found";
        return false;
    }

    const auto boundary = "----SunoBoundary" + juce::Uuid().toString().removeCharacters("-");
    juce::StringPairArray fields;
    fields.set("normalizeOnImport", normalizeOnImport ? "true" : "false");

    auto body = buildMultipartBody(boundary, fields, "file", &source, "application/octet-stream");

    HttpResponse response;
    if (! executeMultipart("/assets/import",
                           "multipart/form-data; boundary=" + boundary,
                           body,
                           response,
                           errorOut))
        return false;

    if (response.statusCode < 200 || response.statusCode >= 300)
        return parseErrorPayload(response.payload, errorOut);

    outAssetId = response.payload.getProperty("assetId", juce::var()).toString();
    if (outAssetId.isEmpty())
    {
        errorOut = "Asset import returned empty assetId";
        return false;
    }

    return true;
}

bool BridgeHttpClient::createAudioJob(const juce::String& assetId,
                                      const juce::String& prompt,
                                      const juce::var& metadata,
                                      JobSummary& outJob,
                                      juce::String& errorOut)
{
    const auto boundary = "----SunoBoundary" + juce::Uuid().toString().removeCharacters("-");
    juce::StringPairArray fields;
    fields.set("clientRequestId", makeRequestId());
    fields.set("prompt", prompt);
    fields.set("metadata", juce::JSON::toString(metadata));
    fields.set("assetId", assetId);

    auto body = buildMultipartBody(boundary, fields, {}, nullptr, {});

    HttpResponse response;
    if (! executeMultipart("/jobs/audio",
                           "multipart/form-data; boundary=" + boundary,
                           body,
                           response,
                           errorOut))
        return false;

    if (response.statusCode < 200 || response.statusCode >= 300)
        return parseErrorPayload(response.payload, errorOut);

    return parseJobFromPayload(response.payload.getProperty("job", juce::var()), outJob, errorOut);
}

bool BridgeHttpClient::createAudioJobWithFile(const juce::File& source,
                                              const juce::String& prompt,
                                              const juce::var& metadata,
                                              JobSummary& outJob,
                                              juce::String& errorOut)
{
    if (! source.existsAsFile())
    {
        errorOut = "Audio source file not found";
        return false;
    }

    const auto boundary = "----SunoBoundary" + juce::Uuid().toString().removeCharacters("-");
    juce::StringPairArray fields;
    fields.set("clientRequestId", makeRequestId());
    fields.set("prompt", prompt);
    fields.set("metadata", juce::JSON::toString(metadata));

    auto body = buildMultipartBody(boundary, fields, "file", &source, "application/octet-stream");

    HttpResponse response;
    if (! executeMultipart("/jobs/audio",
                           "multipart/form-data; boundary=" + boundary,
                           body,
                           response,
                           errorOut))
        return false;

    if (response.statusCode < 200 || response.statusCode >= 300)
        return parseErrorPayload(response.payload, errorOut);

    return parseJobFromPayload(response.payload.getProperty("job", juce::var()), outJob, errorOut);
}

bool BridgeHttpClient::getJob(const juce::String& jobId,
                              JobSummary& outJob,
                              juce::String& errorOut)
{
    HttpResponse response;
    if (! executeJson("GET", "/jobs/" + jobId, "", response, errorOut))
        return false;

    if (response.statusCode < 200 || response.statusCode >= 300)
        return parseErrorPayload(response.payload, errorOut);

    return parseJobFromPayload(response.payload, outJob, errorOut);
}

bool BridgeHttpClient::cancelJob(const juce::String& jobId,
                                 JobSummary& outJob,
                                 juce::String& errorOut)
{
    HttpResponse response;
    if (! executeJson("POST", "/jobs/" + jobId + "/cancel", "{}", response, errorOut))
        return false;

    if (response.statusCode < 200 || response.statusCode >= 300)
        return parseErrorPayload(response.payload, errorOut);

    return parseJobFromPayload(response.payload, outJob, errorOut);
}

juce::String BridgeHttpClient::buildBaseUrl() const
{
    return "http://" + discovery.host + ":" + juce::String(discovery.port);
}

bool BridgeHttpClient::executeJson(const juce::String& method,
                                   const juce::String& path,
                                   const juce::String& jsonBody,
                                   HttpResponse& out,
                                   juce::String& errorOut)
{
    return executeRequest(method,
                          path,
                          "application/json",
                          jsonBody.toRawUTF8(),
                          static_cast<size_t>(jsonBody.getNumBytesAsUTF8()),
                          out,
                          errorOut);
}

bool BridgeHttpClient::executeMultipart(const juce::String& path,
                                        const juce::String& contentType,
                                        const juce::MemoryBlock& body,
                                        HttpResponse& out,
                                        juce::String& errorOut)
{
    return executeRequest("POST", path, contentType, body.getData(), body.getSize(), out, errorOut);
}

bool BridgeHttpClient::executeRequest(const juce::String& method,
                                      const juce::String& path,
                                      const juce::String& contentType,
                                      const void* bodyData,
                                      size_t bodySize,
                                      HttpResponse& out,
                                      juce::String& errorOut)
{
    juce::StringArray headers;
    const auto requestId = makeRequestId();
    const auto nonce = makeRequestId();
    const auto timestamp = juce::String(static_cast<int64>(juce::Time::getCurrentTime().toMilliseconds() / 1000));
    const auto bodyHash = sha256Hex(bodyData, bodySize);
    const auto signature = buildSignature(timestamp, nonce, bodyHash);

    headers.add("X-Plugin-Version: " + config.pluginVersion);
    headers.add("X-Protocol-Version: " + config.protocolVersion);
    headers.add("X-Request-ID: " + requestId);
    headers.add("X-Signature-Timestamp: " + timestamp);
    headers.add("X-Signature-Nonce: " + nonce);
    headers.add("X-Body-Sha256: " + bodyHash);
    headers.add("X-Signature: " + signature);
    headers.add("Content-Type: " + contentType);

    int statusCode = 0;
    auto endpoint = juce::URL(buildBaseUrl() + path);
    auto stream = endpoint.createInputStream(
        juce::URL::InputStreamOptions(juce::URL::ParameterHandling::inAddress)
            .withExtraHeaders(headers.joinIntoString("\n"))
            .withHttpRequestCmd(method)
            .withConnectionTimeoutMs(8000)
            .withStatusCode(&statusCode)
            .withNumRedirectsToFollow(2)
            .withPOSTData(bodyData, bodySize));

    if (stream == nullptr)
    {
        errorOut = "Bridge request failed: could not open stream";
        return false;
    }

    out.statusCode = statusCode;
    out.rawBody = stream->readEntireStreamAsString();
    out.payload = juce::JSON::parse(out.rawBody);
    if (out.payload.isVoid())
    {
        out.payload = juce::var(new juce::DynamicObject());
        out.payload.getDynamicObject()->setProperty("raw", out.rawBody);
    }

    return true;
}

bool BridgeHttpClient::parseJobFromPayload(const juce::var& payload, JobSummary& outJob, juce::String& errorOut) const
{
    if (! payload.isObject())
    {
        errorOut = "Job payload is not an object";
        return false;
    }

    auto* obj = payload.getDynamicObject();
    outJob.id = obj->getProperty("id").toString();
    outJob.type = obj->getProperty("type").toString();
    outJob.status = obj->getProperty("status").toString();
    outJob.remoteJobId = obj->getProperty("remoteJobId").toString();
    outJob.progress = static_cast<float>(obj->getProperty("progress"));
    outJob.lastError = obj->getProperty("lastError").toString();
    outJob.outputAssets.clear();

    if (auto outputAssets = obj->getProperty("outputAssets"); outputAssets.isArray())
        for (const auto& asset : *outputAssets.getArray())
            outJob.outputAssets.add(asset.toString());

    if (outJob.id.isEmpty())
    {
        errorOut = "Job payload missing id";
        return false;
    }

    return true;
}

bool BridgeHttpClient::parseErrorPayload(const juce::var& payload, juce::String& errorOut) const
{
    if (! payload.isObject())
    {
        errorOut = "Unknown bridge error";
        return false;
    }

    auto error = payload.getProperty("error", juce::var());
    if (! error.isObject())
    {
        errorOut = "Bridge request failed without canonical error payload";
        return false;
    }

    auto* obj = error.getDynamicObject();
    const auto code = obj->getProperty("code").toString();
    const auto message = obj->getProperty("message").toString();
    errorOut = code + ": " + message;
    return false;
}

juce::String BridgeHttpClient::buildSignature(const juce::String& timestamp,
                                              const juce::String& nonce,
                                              const juce::String& bodySha256Hex) const
{
    const auto payload = timestamp + "." + nonce + "." + bodySha256Hex;
    return hmacSha256Hex(config.sharedSecret, payload);
}
} // namespace suno::bridge
