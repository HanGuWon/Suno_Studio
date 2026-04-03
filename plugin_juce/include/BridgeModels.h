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

enum class ProviderMode
{
    MockSuno,
    ManualSuno,
};

enum class ClientMode
{
    Song,
    Sound,
    AudioPrompt,
};

enum class RequestedOutputFamily
{
    Mix,
    Stems,
    TempoLockedStems,
    Midi,
};

struct HandoffInfo
{
    juce::String jobId;
    ProviderMode providerMode { ProviderMode::MockSuno };
    juce::File workspace;
    juce::File instructionsPath;
    juce::var handoff;
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
    juce::var outputManifest;
    ProviderMode providerMode { ProviderMode::MockSuno };
    juce::var providerMetadata;
};

struct ClientConfig
{
    juce::String pluginVersion { "0.1.0" };
    juce::String protocolVersion { "1.3" };
    juce::String sharedSecret { "dev-shared-secret" };
};

juce::String toApiString(ProviderMode mode);
juce::String toApiString(ClientMode mode);
juce::String toApiString(RequestedOutputFamily family);

ProviderMode providerModeFromString(const juce::String& value);
ClientMode clientModeFromString(const juce::String& value);
RequestedOutputFamily requestedOutputFamilyFromString(const juce::String& value);

juce::StringArray requestedOutputsToApi(const juce::Array<RequestedOutputFamily>& families);
juce::Array<RequestedOutputFamily> requestedOutputsFromApi(const juce::var& values);

bool isManualWaitingState(const juce::String& status);
} // namespace suno::bridge
