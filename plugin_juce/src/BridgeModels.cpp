#include "BridgeModels.h"

namespace suno::bridge
{
juce::String toApiString(ProviderMode mode)
{
    return mode == ProviderMode::ManualSuno ? "manual_suno" : "mock_suno";
}

juce::String toApiString(ClientMode mode)
{
    switch (mode)
    {
        case ClientMode::Song: return "song";
        case ClientMode::Sound: return "sound";
        case ClientMode::AudioPrompt: return "audio_prompt";
    }

    return "song";
}

juce::String toApiString(RequestedOutputFamily family)
{
    switch (family)
    {
        case RequestedOutputFamily::Mix: return "mix";
        case RequestedOutputFamily::Stems: return "stems";
        case RequestedOutputFamily::TempoLockedStems: return "tempo_locked_stems";
        case RequestedOutputFamily::Midi: return "midi";
    }

    return "mix";
}

ProviderMode providerModeFromString(const juce::String& value)
{
    return value.trim().equalsIgnoreCase("manual_suno") ? ProviderMode::ManualSuno : ProviderMode::MockSuno;
}

ClientMode clientModeFromString(const juce::String& value)
{
    if (value.equalsIgnoreCase("sound"))
        return ClientMode::Sound;
    if (value.equalsIgnoreCase("audio_prompt"))
        return ClientMode::AudioPrompt;
    return ClientMode::Song;
}

RequestedOutputFamily requestedOutputFamilyFromString(const juce::String& value)
{
    if (value.equalsIgnoreCase("stems"))
        return RequestedOutputFamily::Stems;
    if (value.equalsIgnoreCase("tempo_locked_stems") || value.equalsIgnoreCase("tempoLockedStems"))
        return RequestedOutputFamily::TempoLockedStems;
    if (value.equalsIgnoreCase("midi"))
        return RequestedOutputFamily::Midi;
    return RequestedOutputFamily::Mix;
}

juce::StringArray requestedOutputsToApi(const juce::Array<RequestedOutputFamily>& families)
{
    juce::StringArray out;
    for (auto family : families)
        out.addIfNotAlreadyThere(toApiString(family));
    return out;
}

juce::Array<RequestedOutputFamily> requestedOutputsFromApi(const juce::var& values)
{
    juce::Array<RequestedOutputFamily> out;
    if (! values.isArray())
        return out;

    for (const auto& v : *values.getArray())
    {
        auto parsed = requestedOutputFamilyFromString(v.toString());
        if (! out.contains(parsed))
            out.add(parsed);
    }
    return out;
}

bool isManualWaitingState(const juce::String& status)
{
    return status == "awaiting_manual_provider_submission"
        || status == "awaiting_manual_provider_result"
        || status == "importing_provider_result";
}
} // namespace suno::bridge
