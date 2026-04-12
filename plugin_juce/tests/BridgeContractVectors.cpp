#include <juce_core/juce_core.h>
#include <cstring>

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

juce::var loadJsonFixture(const juce::String& relativePath)
{
    auto fixtureFile = juce::File::getCurrentWorkingDirectory().getChildFile(relativePath);
    expect(fixtureFile.existsAsFile(), "fixture exists: " + relativePath);
    if (! fixtureFile.existsAsFile())
        return {};

    auto parsed = juce::JSON::parse(fixtureFile);
    expect(parsed.isObject(), "fixture parses as object: " + relativePath);
    return parsed;
}

juce::String sha256Hex(const void* data, size_t size)
{
    juce::SHA256 digest(data, size);
    return digest.toHexString();
}

juce::MemoryBlock sha256Raw(const void* data, size_t size)
{
    juce::SHA256 digest(data, size);
    juce::MemoryBlock out;
    out.append(digest.getRawData(), 32);
    return out;
}

juce::String hmacSha256Hex(const juce::String& key, const juce::String& message)
{
    constexpr size_t blockSize = 64;
    juce::MemoryBlock keyBlock;
    keyBlock.append(key.toRawUTF8(), static_cast<size_t>(key.getNumBytesAsUTF8()));

    if (keyBlock.getSize() > blockSize)
        keyBlock = sha256Raw(keyBlock.getData(), keyBlock.getSize());

    if (keyBlock.getSize() < blockSize)
    {
        juce::HeapBlock<uint8_t> zeros(blockSize - keyBlock.getSize());
        std::memset(zeros.get(), 0, blockSize - keyBlock.getSize());
        keyBlock.append(zeros.get(), blockSize - keyBlock.getSize());
    }

    juce::MemoryBlock outerPad;
    juce::MemoryBlock innerPad;
    outerPad.setSize(blockSize);
    innerPad.setSize(blockSize);

    auto* keyBytes = static_cast<const uint8_t*>(keyBlock.getData());
    auto* outerBytes = static_cast<uint8_t*>(outerPad.getData());
    auto* innerBytes = static_cast<uint8_t*>(innerPad.getData());

    for (size_t i = 0; i < blockSize; ++i)
    {
        outerBytes[i] = static_cast<uint8_t>(keyBytes[i] ^ 0x5c);
        innerBytes[i] = static_cast<uint8_t>(keyBytes[i] ^ 0x36);
    }

    juce::MemoryBlock inner;
    inner.append(innerPad.getData(), innerPad.getSize());
    inner.append(message.toRawUTF8(), static_cast<size_t>(message.getNumBytesAsUTF8()));
    auto innerHash = sha256Raw(inner.getData(), inner.getSize());

    juce::MemoryBlock outer;
    outer.append(outerPad.getData(), outerPad.getSize());
    outer.append(innerHash.getData(), innerHash.getSize());
    return sha256Hex(outer.getData(), outer.getSize());
}

void validateSigningVectors(const juce::var& vectors)
{
    const auto sharedSecret = vectors.getProperty("shared_secret", juce::var()).toString();
    expect(sharedSecret.isNotEmpty(), "signing vectors include shared_secret");

    const auto cases = vectors.getProperty("cases", juce::var());
    expect(cases.isArray(), "signing vectors include cases[]");
    if (! cases.isArray())
        return;

    for (const auto& item : *cases.getArray())
    {
        expect(item.isObject(), "signing case is object");
        if (! item.isObject())
            continue;

        const auto timestamp = item.getProperty("timestamp", juce::var()).toString();
        const auto nonce = item.getProperty("nonce", juce::var()).toString();
        const auto body = item.getProperty("body", juce::var()).toString();
        const auto expectedBodyHash = item.getProperty("expected_body_sha256", juce::var()).toString();
        const auto expectedSignature = item.getProperty("expected_signature", juce::var()).toString();

        const auto bodyHash = sha256Hex(body.toRawUTF8(), static_cast<size_t>(body.getNumBytesAsUTF8()));
        expect(bodyHash == expectedBodyHash, "body sha256 parity for nonce=" + nonce);

        const auto payload = timestamp + "." + nonce + "." + bodyHash;
        const auto signature = hmacSha256Hex(sharedSecret, payload);
        expect(signature == expectedSignature, "HMAC signature parity for nonce=" + nonce);
    }
}

void validateMultipartVectors(const juce::var& vectors)
{
    const auto prefix = vectors.getProperty("content_type_prefix", juce::var()).toString();
    expect(prefix == "multipart/form-data; boundary=", "multipart content_type_prefix");

    const auto assetImport = vectors.getProperty("asset_import", juce::var());
    const auto audioJob = vectors.getProperty("audio_job", juce::var());
    const auto manualComplete = vectors.getProperty("manual_complete", juce::var());

    expect(assetImport.isObject(), "multipart vectors include asset_import object");
    expect(audioJob.isObject(), "multipart vectors include audio_job object");
    expect(manualComplete.isObject(), "multipart vectors include manual_complete object");

    auto requiredAssetFields = assetImport.getProperty("required_fields", juce::var());
    expect(requiredAssetFields.isArray(), "asset_import.required_fields array");
    if (requiredAssetFields.isArray())
    {
        expect(requiredAssetFields.getArray()->contains("normalizeOnImport"), "asset_import has normalizeOnImport field");
        expect(requiredAssetFields.getArray()->contains("file"), "asset_import has file field");
    }

    auto requiredAudioFields = audioJob.getProperty("required_fields", juce::var());
    expect(requiredAudioFields.isArray(), "audio_job.required_fields array");
    if (requiredAudioFields.isArray())
    {
        expect(requiredAudioFields.getArray()->contains("clientRequestId"), "audio_job has clientRequestId field");
        expect(requiredAudioFields.getArray()->contains("prompt"), "audio_job has prompt field");
        expect(requiredAudioFields.getArray()->contains("metadata"), "audio_job has metadata field");
        expect(requiredAudioFields.getArray()->contains("providerMode"), "audio_job has providerMode field");
    }

    auto optionalAudioFields = audioJob.getProperty("optional_fields", juce::var());
    expect(optionalAudioFields.isArray(), "audio_job.optional_fields array");
    if (optionalAudioFields.isArray())
    {
        expect(optionalAudioFields.getArray()->contains("assetId"), "audio_job supports assetId field");
        expect(optionalAudioFields.getArray()->contains("file"), "audio_job supports file field");
    }

    auto requiredManualFields = manualComplete.getProperty("required_fields", juce::var());
    expect(requiredManualFields.isArray(), "manual_complete.required_fields array");
    if (requiredManualFields.isArray())
    {
        expect(requiredManualFields.getArray()->contains("mixFiles"), "manual_complete has mixFiles field");
        expect(requiredManualFields.getArray()->contains("stemFiles"), "manual_complete has stemFiles field");
        expect(requiredManualFields.getArray()->contains("tempoLockedStemFiles"), "manual_complete has tempoLockedStemFiles field");
        expect(requiredManualFields.getArray()->contains("midiFiles"), "manual_complete has midiFiles field");
    }
}

void validateManualContractVectors(const juce::var& vectors)
{
    using namespace suno::bridge;

    const auto providerModes = vectors.getProperty("provider_modes", juce::var());
    expect(providerModes.isArray(), "manual contract includes provider_modes");
    if (providerModes.isArray())
    {
        for (const auto& item : *providerModes.getArray())
        {
            auto mode = item.toString();
            expect(toApiString(providerModeFromString(mode)) == mode, "provider mode round-trip: " + mode);
        }
    }

    const auto requestedOutputs = vectors.getProperty("requested_outputs", juce::var());
    expect(requestedOutputs.isArray(), "manual contract includes requested_outputs");
    if (requestedOutputs.isArray())
    {
        juce::Array<RequestedOutputFamily> parsedFamilies;
        for (const auto& family : *requestedOutputs.getArray())
            parsedFamilies.addIfNotAlreadyThere(requestedOutputFamilyFromString(family.toString()));

        auto serialized = requestedOutputsToApi(parsedFamilies);
        for (const auto& family : *requestedOutputs.getArray())
            expect(serialized.contains(family.toString()), "requested output round-trip: " + family.toString());
    }

    const auto waitingStates = vectors.getProperty("manual_waiting_states", juce::var());
    expect(waitingStates.isArray(), "manual contract includes manual_waiting_states");
    if (waitingStates.isArray())
    {
        for (const auto& state : *waitingStates.getArray())
            expect(isManualWaitingState(state.toString()), "manual waiting state recognized: " + state.toString());
    }

    const auto manualFields = vectors.getProperty("manual_complete_fields", juce::var());
    expect(manualFields.isArray(), "manual contract includes manual_complete_fields");

    auto canonicalError = vectors.getProperty("canonical_error_shape", juce::var());
    expect(canonicalError.isObject(), "manual contract includes canonical_error_shape");
    auto errorObj = canonicalError.getProperty("error", juce::var());
    expect(errorObj.isObject(), "canonical_error_shape.error is object");
    if (errorObj.isObject())
    {
        auto* error = errorObj.getDynamicObject();
        expect(error->hasProperty("code"), "canonical error contains code");
        expect(error->hasProperty("message"), "canonical error contains message");
        expect(error->hasProperty("details"), "canonical error contains details");
        expect(error->hasProperty("request_id"), "canonical error contains request_id");
    }
}
} // namespace

int main()
{
    auto signingVectors = loadJsonFixture("plugin_juce/test_vectors/signing_vectors.json");
    auto multipartVectors = loadJsonFixture("plugin_juce/test_vectors/multipart_vectors.json");
    auto manualVectors = loadJsonFixture("plugin_juce/test_vectors/manual_contract_vectors.json");

    if (signingVectors.isObject())
        validateSigningVectors(signingVectors);
    if (multipartVectors.isObject())
        validateMultipartVectors(multipartVectors);
    if (manualVectors.isObject())
        validateManualContractVectors(manualVectors);

    juce::Logger::writeToLog(failures == 0 ? "Bridge contract vectors PASS" : "Bridge contract vectors FAIL");
    return failures == 0 ? 0 : 1;
}
