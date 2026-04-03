#pragma once

#include "BridgeModels.h"

namespace suno::bridge
{
class BridgeHttpClient
{
public:
    BridgeHttpClient(DiscoveryInfo discovery, ClientConfig config);

    bool handshake(juce::String& errorOut);
    bool createTextJob(const juce::String& prompt, const juce::var& metadata, JobSummary& outJob, juce::String& errorOut);
    bool importAsset(const juce::File& source, bool normalizeOnImport, juce::String& outAssetId, juce::String& errorOut);
    bool createAudioJob(const juce::String& assetId, const juce::String& prompt, const juce::var& metadata, JobSummary& outJob, juce::String& errorOut);
    bool createAudioJobWithFile(const juce::File& source, const juce::String& prompt, const juce::var& metadata, JobSummary& outJob, juce::String& errorOut);
    bool getJob(const juce::String& jobId, JobSummary& outJob, juce::String& errorOut);
    bool cancelJob(const juce::String& jobId, JobSummary& outJob, juce::String& errorOut);

private:
    struct HttpResponse
    {
        int statusCode { 0 };
        juce::var payload;
        juce::String rawBody;
    };

    juce::String buildBaseUrl() const;

    bool executeJson(const juce::String& method,
                     const juce::String& path,
                     const juce::String& jsonBody,
                     HttpResponse& out,
                     juce::String& errorOut);

    bool executeMultipart(const juce::String& path,
                          const juce::String& contentType,
                          const juce::MemoryBlock& body,
                          HttpResponse& out,
                          juce::String& errorOut);

    bool executeRequest(const juce::String& method,
                        const juce::String& path,
                        const juce::String& contentType,
                        const void* bodyData,
                        size_t bodySize,
                        HttpResponse& out,
                        juce::String& errorOut);

    bool parseJobFromPayload(const juce::var& payload, JobSummary& outJob, juce::String& errorOut) const;
    bool parseErrorPayload(const juce::var& payload, juce::String& errorOut) const;

    juce::String buildSignature(const juce::String& timestamp,
                                const juce::String& nonce,
                                const juce::String& bodySha256Hex) const;

    DiscoveryInfo discovery;
    ClientConfig config;
};
} // namespace suno::bridge
