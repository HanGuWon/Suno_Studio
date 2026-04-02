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
    bool importAsset(const juce::File& source, juce::String& outAssetId, juce::String& errorOut);
    bool createAudioJob(const juce::String& assetId, const juce::String& prompt, const juce::var& metadata, JobSummary& outJob, juce::String& errorOut);
    bool getJob(const juce::String& jobId, JobSummary& outJob, juce::String& errorOut);
    bool cancelJob(const juce::String& jobId, JobSummary& outJob, juce::String& errorOut);

private:
    juce::String buildBaseUrl() const;
    bool executeJson(const juce::String& method,
                     const juce::String& path,
                     const juce::String& body,
                     juce::var& response,
                     juce::String& errorOut);

    DiscoveryInfo discovery;
    ClientConfig config;
};
} // namespace suno::bridge
