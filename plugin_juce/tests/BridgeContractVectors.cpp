#include <juce_core/juce_core.h>

#include "BridgeModels.h"

static int failures = 0;

void expect(bool cond, const juce::String& message)
{
    if (! cond)
    {
        ++failures;
        juce::Logger::writeToLog("FAIL: " + message);
    }
}

int main()
{
    using namespace suno::bridge;

    expect(toApiString(ProviderMode::MockSuno) == "mock_suno", "provider mode serialize mock");
    expect(toApiString(ProviderMode::ManualSuno) == "manual_suno", "provider mode serialize manual");
    expect(providerModeFromString("manual_suno") == ProviderMode::ManualSuno, "provider mode parse manual");

    juce::Array<RequestedOutputFamily> families { RequestedOutputFamily::Mix, RequestedOutputFamily::Midi };
    auto serialized = requestedOutputsToApi(families);
    expect(serialized.contains("mix") && serialized.contains("midi"), "requested outputs serialize");

    juce::Array<juce::var> asVar;
    asVar.add("mix");
    asVar.add("tempoLockedStems");
    auto parsed = requestedOutputsFromApi(asVar);
    expect(parsed.contains(RequestedOutputFamily::Mix), "requested outputs parse mix");
    expect(parsed.contains(RequestedOutputFamily::TempoLockedStems), "requested outputs parse tempoLockedStems");

    juce::var errorPayload = juce::JSON::parse(R"({"error":{"code":"HANDOFF_NOT_READY","message":"Manual handoff package has not been prepared yet.","details":{"jobId":"abc"},"request_id":"req-1"}})");
    expect(errorPayload.isObject(), "canonical error parses");

    juce::File vectorFile = juce::File::getCurrentWorkingDirectory().getChildFile("plugin_juce/test_vectors/manual_contract_vectors.json");
    juce::DynamicObject vectors;
    vectors.setProperty("provider_modes", juce::Array<juce::var>{"mock_suno", "manual_suno"});
    vectors.setProperty("manual_waiting_states", juce::Array<juce::var>{"awaiting_manual_provider_submission", "awaiting_manual_provider_result", "importing_provider_result"});
    vectors.setProperty("manual_complete_fields", juce::Array<juce::var>{"mixFiles", "stemFiles", "tempoLockedStemFiles", "midiFiles"});
    vectorFile.getParentDirectory().createDirectory();
    vectorFile.replaceWithText(juce::JSON::toString(&vectors, true));

    juce::Logger::writeToLog(failures == 0 ? "Bridge contract vectors PASS" : "Bridge contract vectors FAIL");
    return failures == 0 ? 0 : 1;
}
