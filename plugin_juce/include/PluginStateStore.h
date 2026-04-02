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
    juce::String mode { "song" };
    bool soundLoop { false };
    int bpmHint { 120 };
    juce::String keyHint { "Am" };
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
