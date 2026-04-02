#pragma once

#include <juce_core/juce_core.h>

namespace suno::bridge
{
struct DiscoveryInfo
{
    juce::String host { "127.0.0.1" };
    int port { 7071 };
    juce::String protocolMin { "1.2" };
    juce::String protocolMax { "1.3" };
    bool hmacRequired { true };
};

struct JobSummary
{
    juce::String id;
    juce::String type;
    juce::String status;
    juce::String remoteJobId;
    float progress { 0.0f };
    juce::String lastError;
    juce::StringArray outputAssets;
};

struct ClientConfig
{
    juce::String pluginVersion { "0.1.0" };
    juce::String protocolVersion { "1.3" };
    juce::String sharedSecret { "dev-shared-secret" };
};
} // namespace suno::bridge
