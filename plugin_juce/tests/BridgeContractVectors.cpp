#include <juce_core/juce_core.h>

#include "BridgeHttpClient.h"
#include "BridgeModels.h"

namespace
{
int failures = 0;

void expect(bool cond, const juce::String& message)
{
    if (! cond)
    {
        ++failures;
        juce::Logger::writeToLog("FAIL: " + message);
    }
}

juce::var readJson(const juce::File& file)
{
    expect(file.existsAsFile(), "fixture exists: " + file.getFullPathName());
    return juce::JSON::parse(file);
}

bool containsAll(const juce::StringArray& haystack, const juce::Array<juce::var>& expected)
{
    for (const auto& value : expected)
        if (! haystack.contains(value.toString()))
            return false;
    return true;
}
}

int main()
{
    using namespace suno::bridge;

    const auto root = juce::File::getCurrentWorkingDirectory().getChildFile("plugin_juce/test_vectors");
    const auto signingVectors = readJson(root.getChildFile("signing_vectors.json"));
    const auto multipartVectors = readJson(root.getChildFile("multipart_vectors.json"));
    const auto manualVectors = readJson(root.getChildFile("manual_contract_vectors.json"));

    expect(toApiString(ProviderMode::MockSuno) == "mock_suno", "provider mode serialize mock");
    expect(toApiString(ProviderMode::ManualSuno) == "manual_suno", "provider mode serialize manual");
    expect(providerModeFromString("manual_suno") == ProviderMode::ManualSuno, "provider mode parse manual");

    juce::Array<RequestedOutputFamily> families { RequestedOutputFamily::Mix, RequestedOutputFamily::Midi };
    auto serialized = requestedOutputsToApi(families);
    expect(serialized.contains("mix") && serialized.contains("midi"), "requested outputs serialize");
    auto parsed = requestedOutputsFromApi(juce::Array<juce::var>{ "mix", "tempoLockedStems" });
    expect(parsed.contains(RequestedOutputFamily::TempoLockedStems), "requested outputs parse tempo locked stems");

    for (const auto& state : *manualVectors.getProperty("manual_waiting_states", juce::var()).getArray())
        expect(isManualWaitingState(state.toString()), "manual waiting state recognized: " + state.toString());

    auto canonicalError = manualVectors.getProperty("canonical_error_shape", juce::var());
    expect(canonicalError.isObject(), "canonical error fixture is object");
    auto errObj = canonicalError.getProperty("error", juce::var());
    expect(errObj.isObject(), "canonical error.error is object");
    expect(errObj.getProperty("code", juce::var()).toString().isNotEmpty(), "canonical error has code");
    expect(errObj.getProperty("message", juce::var()).toString().isNotEmpty(), "canonical error has message");

    auto sharedSecret = signingVectors.getProperty("shared_secret", juce::var()).toString();
    auto cases = signingVectors.getProperty("cases", juce::var());
    expect(cases.isArray(), "signing vector cases are array");
    if (cases.isArray())
    {
        for (const auto& c : *cases.getArray())
        {
            const auto body = c.getProperty("body", juce::var()).toString();
            const auto timestamp = c.getProperty("timestamp", juce::var()).toString();
            const auto nonce = c.getProperty("nonce", juce::var()).toString();
            const auto expectedSha = c.getProperty("expected_body_sha256", juce::var()).toString();
            const auto expectedSignature = c.getProperty("expected_signature", juce::var()).toString();

            const auto actualSha = BridgeHttpClient::computeBodySha256Hex(body);
            const auto actualSignature = BridgeHttpClient::computeSignatureHex(sharedSecret, timestamp, nonce, actualSha);
            expect(actualSha == expectedSha, "body sha matches vector for nonce=" + nonce);
            expect(actualSignature == expectedSignature, "hmac signature matches vector for nonce=" + nonce);
        }
    }

    auto assetRequired = multipartVectors.getProperty("asset_import", juce::var()).getProperty("required_fields", juce::var());
    auto audioRequired = multipartVectors.getProperty("audio_job", juce::var()).getProperty("required_fields", juce::var());
    auto audioOptional = multipartVectors.getProperty("audio_job", juce::var()).getProperty("optional_fields", juce::var());
    auto manualRequired = multipartVectors.getProperty("manual_complete", juce::var()).getProperty("required_fields", juce::var());

    expect(assetRequired.isArray(), "asset required fields vector present");
    expect(audioRequired.isArray(), "audio required fields vector present");
    expect(audioOptional.isArray(), "audio optional fields vector present");
    expect(manualRequired.isArray(), "manual complete fields vector present");

    expect(containsAll(BridgeHttpClient::assetImportRequiredFields(), *assetRequired.getArray()), "asset import fields match fixture");
    expect(containsAll(BridgeHttpClient::audioJobRequiredFields(), *audioRequired.getArray()), "audio job fields match fixture");
    expect(containsAll(BridgeHttpClient::audioJobOptionalFields(), *audioOptional.getArray()), "audio job optional fields match fixture");
    expect(containsAll(BridgeHttpClient::manualCompleteFieldNames(), *manualRequired.getArray()), "manual complete fields match fixture");

    juce::Logger::writeToLog(failures == 0 ? "Bridge contract vectors PASS" : "Bridge contract vectors FAIL");
    return failures == 0 ? 0 : 1;
}
