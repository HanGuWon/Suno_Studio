#pragma once

#include "BridgeDiscovery.h"
#include "BridgeHttpClient.h"
#include "PluginStateStore.h"

namespace suno::bridge
{
class BridgeController
{
public:
    BridgeController(PluginStateStore stateStore, ClientConfig clientConfig);

    bool connectWithDiscovery(const juce::File& lockfile, const juce::String& sharedSecretOverride, juce::String& errorOut);
    bool connectDev(const juce::String& host, int port, const juce::String& sharedSecret, juce::String& errorOut);
    void disconnect();

    bool submitText(const juce::String& prompt, const juce::var& metadata, juce::String& errorOut);
    bool importAndSubmitAudio(const juce::File& source, const juce::String& prompt, const juce::var& metadata, juce::String& errorOut);
    bool cancelActive(juce::String& errorOut);
    bool pollActive(juce::String& errorOut);

    bool isConnected() const { return connected; }
    const JobSummary& getActiveJob() const { return activeJob; }
    const juce::StringArray& getOutputFiles() const { return outputFiles; }
    const PluginState& getState() const { return state; }

    void selectOutputFile(const juce::String& path);

private:
    void persist();

    PluginStateStore stateStore;
    ClientConfig config;
    PluginState state;

    std::unique_ptr<BridgeHttpClient> client;
    bool connected { false };
    JobSummary activeJob;
    juce::StringArray outputFiles;
};
} // namespace suno::bridge
