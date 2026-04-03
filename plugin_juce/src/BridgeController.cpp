#include "BridgeController.h"

namespace suno::bridge
{
BridgeController::BridgeController(PluginStateStore store, ClientConfig clientConfig)
    : stateStore(std::move(store)), config(std::move(clientConfig))
{
    state = stateStore.load();
    if (state.lastSelectedOutputPath.isNotEmpty())
        outputFiles.add(state.lastSelectedOutputPath);

    lastHandoff.jobId = state.lastHandoffJobId;
    lastHandoff.workspace = state.lastHandoffWorkspace;
    lastHandoff.instructionsPath = state.lastHandoffInstructions;
    lastHandoff.providerMode = state.providerMode;
}

bool BridgeController::connectWithDiscovery(const juce::File& lockfile,
                                            const juce::String& sharedSecretOverride,
                                            juce::String& errorOut)
{
    auto discovery = BridgeDiscovery(lockfile).discover();
    auto localConfig = config;
    if (sharedSecretOverride.isNotEmpty())
        localConfig.sharedSecret = sharedSecretOverride;

    client.reset(new BridgeHttpClient(discovery, localConfig));
    if (! client->handshake(errorOut))
    {
        connected = false;
        return false;
    }

    state.discoveryCachePath = lockfile;
    connected = true;
    persist();
    return true;
}

bool BridgeController::connectDev(const juce::String& host,
                                  int port,
                                  const juce::String& sharedSecret,
                                  juce::String& errorOut)
{
    DiscoveryInfo discovery;
    discovery.host = host;
    discovery.port = port;

    auto localConfig = config;
    localConfig.sharedSecret = sharedSecret;
    client.reset(new BridgeHttpClient(discovery, localConfig));

    if (! client->handshake(errorOut))
    {
        connected = false;
        return false;
    }

    connected = true;
    persist();
    return true;
}

void BridgeController::disconnect()
{
    client.reset();
    connected = false;
}

JobCreateOptions BridgeController::makeJobOptions() const
{
    JobCreateOptions options;
    options.mode = state.mode;
    options.providerMode = state.providerMode;
    options.requestedOutputs = state.requestedOutputs;
    options.oneShot = state.soundOneShot;
    options.loop = state.soundLoop;
    options.bpm = state.bpmHint;
    options.key = state.keyHint;
    return options;
}

bool BridgeController::submitText(const juce::String& prompt, juce::String& errorOut)
{
    if (! connected || client == nullptr)
    {
        errorOut = "Bridge not connected";
        return false;
    }

    if (! client->createTextJob(prompt, makeJobOptions(), activeJob, errorOut))
        return false;

    state.lastActiveJobId = activeJob.id;
    state.recentJobIds.addIfNotAlreadyThere(activeJob.id);
    persist();
    return true;
}

bool BridgeController::importAndSubmitAudio(const juce::File& source,
                                            const juce::String& prompt,
                                            juce::String& errorOut)
{
    if (! connected || client == nullptr)
    {
        errorOut = "Bridge not connected";
        return false;
    }

    juce::String assetId;
    if (! client->importAsset(source, false, assetId, errorOut))
        return false;

    state.recentAssetIds.addIfNotAlreadyThere(assetId);

    auto options = makeJobOptions();
    options.mode = ClientMode::AudioPrompt;
    if (! client->createAudioJob(assetId, prompt, options, activeJob, errorOut))
        return false;

    state.lastActiveJobId = activeJob.id;
    state.recentJobIds.addIfNotAlreadyThere(activeJob.id);
    persist();
    return true;
}

bool BridgeController::cancelActive(juce::String& errorOut)
{
    if (! connected || client == nullptr || activeJob.id.isEmpty())
    {
        errorOut = "No active job";
        return false;
    }

    return client->cancelJob(activeJob.id, activeJob, errorOut);
}

bool BridgeController::pollActive(juce::String& errorOut)
{
    if (! connected || client == nullptr || activeJob.id.isEmpty())
        return false;

    if (! client->getJob(activeJob.id, activeJob, errorOut))
        return false;

    outputFiles = activeJob.outputAssets;
    if (outputFiles.size() > 0)
        state.lastSelectedOutputPath = outputFiles[0];
    persist();
    return true;
}

bool BridgeController::fetchHandoff(juce::String& errorOut)
{
    if (! connected || client == nullptr || activeJob.id.isEmpty())
    {
        errorOut = "No active job";
        return false;
    }

    if (! client->getHandoff(activeJob.id, lastHandoff, errorOut))
        return false;

    state.lastHandoffJobId = lastHandoff.jobId;
    state.lastHandoffWorkspace = lastHandoff.workspace;
    state.lastHandoffInstructions = lastHandoff.instructionsPath;
    persist();
    return true;
}

bool BridgeController::revealHandoffFolder(juce::String& errorOut) const
{
    if (! lastHandoff.workspace.isDirectory())
    {
        errorOut = "Handoff workspace not available";
        return false;
    }

    lastHandoff.workspace.revealToUser();
    return true;
}

bool BridgeController::openHandoffInstructions(juce::String& errorOut) const
{
    if (! lastHandoff.instructionsPath.existsAsFile())
    {
        errorOut = "Handoff instructions not available";
        return false;
    }

    lastHandoff.instructionsPath.startAsProcess();
    return true;
}

bool BridgeController::manualCompleteActive(const ManualCompleteFiles& files, juce::String& errorOut)
{
    if (! connected || client == nullptr || activeJob.id.isEmpty())
    {
        errorOut = "No active job";
        return false;
    }

    if (! client->manualComplete(activeJob.id, files, activeJob, errorOut))
        return false;

    if (activeJob.outputManifest.isObject())
        state.lastImportedFamilies = activeJob.outputManifest.getProperty("importedDeliverables", juce::var());

    outputFiles = activeJob.outputAssets;
    persist();
    return true;
}

void BridgeController::setProviderMode(ProviderMode mode)
{
    state.providerMode = mode;
    persist();
}

void BridgeController::setMode(ClientMode mode)
{
    state.mode = mode;
    persist();
}

void BridgeController::setSoundOptions(bool oneShot, bool loop, int bpm, const juce::String& key)
{
    state.soundOneShot = oneShot;
    state.soundLoop = loop;
    state.bpmHint = bpm;
    state.keyHint = key;
    persist();
}

void BridgeController::setRequestedOutputs(const juce::Array<RequestedOutputFamily>& outputs)
{
    state.requestedOutputs = outputs;
    if (state.requestedOutputs.isEmpty())
        state.requestedOutputs.add(RequestedOutputFamily::Mix);
    persist();
}

void BridgeController::selectOutputFile(const juce::String& path)
{
    state.lastSelectedOutputPath = path;
    if (path.isNotEmpty())
        outputFiles.addIfNotAlreadyThere(path);
    persist();
}

void BridgeController::persist()
{
    stateStore.save(state);
}
} // namespace suno::bridge
