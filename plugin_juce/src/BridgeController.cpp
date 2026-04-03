#include "BridgeController.h"

namespace suno::bridge
{
BridgeController::BridgeController(PluginStateStore store, ClientConfig clientConfig)
    : stateStore(std::move(store)), config(std::move(clientConfig))
{
    state = stateStore.load();
    if (state.lastSelectedOutputPath.isNotEmpty())
        outputFiles.add(state.lastSelectedOutputPath);
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

bool BridgeController::submitText(const juce::String& prompt,
                                  const juce::var& metadata,
                                  juce::String& errorOut)
{
    if (! connected || client == nullptr)
    {
        errorOut = "Bridge not connected";
        return false;
    }

    if (! client->createTextJob(prompt, metadata, activeJob, errorOut))
        return false;

    state.lastActiveJobId = activeJob.id;
    state.recentJobIds.addIfNotAlreadyThere(activeJob.id);
    persist();
    return true;
}

bool BridgeController::importAndSubmitAudio(const juce::File& source,
                                            const juce::String& prompt,
                                            const juce::var& metadata,
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

    if (! client->createAudioJob(assetId, prompt, metadata, activeJob, errorOut))
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
