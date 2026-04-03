#pragma once

#include "BridgeModels.h"

namespace suno::bridge
{
struct PluginState
{
    juce::File discoveryCachePath;
    juce::StringArray recentJobIds;
    juce::StringArray pendingRequestIds;
    juce::StringArray recentAssetIds;
    ClientMode mode { ClientMode::Song };
    ProviderMode providerMode { ProviderMode::MockSuno };
    juce::Array<RequestedOutputFamily> requestedOutputs { RequestedOutputFamily::Mix };
    bool soundOneShot { true };
    bool soundLoop { false };
    int bpmHint { 120 };
    juce::String keyHint { "Am" };
    juce::String lastSelectedOutputPath;
    juce::String lastActiveJobId;
    juce::String lastHandoffJobId;
    juce::File lastHandoffWorkspace;
    juce::File lastHandoffInstructions;
    juce::var lastImportedFamilies;
};

class PluginStateStore
{
public:
    explicit PluginStateStore(juce::File stateFile);

    PluginState load() const;
    void save(const PluginState& state) const;

private:
    juce::File path;
};
} // namespace suno::bridge
