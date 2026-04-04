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

    bool submitText(const juce::String& prompt, juce::String& errorOut);
    bool importAndSubmitAudio(const juce::File& source, const juce::String& prompt, juce::String& errorOut);
    bool cancelActive(juce::String& errorOut);
    bool pollActive(juce::String& errorOut);
    bool restoreLastActiveJob(juce::String& errorOut);

    bool fetchHandoff(juce::String& errorOut);
    bool revealHandoffFolder(juce::String& errorOut) const;
    bool openHandoffInstructions(juce::String& errorOut) const;
    bool manualCompleteActive(const ManualCompleteFiles& files, juce::String& errorOut);

    void setProviderMode(ProviderMode mode);
    void setMode(ClientMode mode);
    void setSoundOptions(bool oneShot, bool loop, int bpm, const juce::String& key);
    void setRequestedOutputs(const juce::Array<RequestedOutputFamily>& outputs);

    bool isConnected() const { return connected; }
    const JobSummary& getActiveJob() const { return activeJob; }
    const juce::StringArray& getOutputFiles() const { return outputFiles; }
    const PluginState& getState() const { return state; }
    const HandoffInfo& getLastHandoff() const { return lastHandoff; }
    const juce::var& getLastImportedFamilies() const { return state.lastImportedFamilies; }

    void selectOutputFile(const juce::String& path);

private:
    JobCreateOptions makeJobOptions() const;
    void persist();

    PluginStateStore stateStore;
    ClientConfig config;
    PluginState state;

    std::unique_ptr<BridgeHttpClient> client;
    bool connected { false };
    JobSummary activeJob;
    HandoffInfo lastHandoff;
    juce::StringArray outputFiles;
};
} // namespace suno::bridge
