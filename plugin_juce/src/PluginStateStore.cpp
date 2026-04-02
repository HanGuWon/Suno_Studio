#include "PluginStateStore.h"

namespace suno::bridge
{
PluginStateStore::PluginStateStore(juce::File stateFile)
    : path(std::move(stateFile))
{
}

PluginState PluginStateStore::load() const
{
    PluginState state;
    if (! path.existsAsFile())
        return state;

    const auto parsed = juce::JSON::parse(path);
    if (! parsed.isObject())
        return state;

    auto* obj = parsed.getDynamicObject();
    state.discoveryCachePath = juce::File(obj->getProperty("discoveryCachePath").toString());
    state.mode = obj->getProperty("mode").toString();
    state.soundLoop = static_cast<bool>(obj->getProperty("soundLoop"));
    state.bpmHint = static_cast<int>(obj->getProperty("bpmHint"));
    state.keyHint = obj->getProperty("keyHint").toString();
    state.lastSelectedOutputPath = obj->getProperty("lastSelectedOutputPath").toString();
    state.lastActiveJobId = obj->getProperty("lastActiveJobId").toString();

    if (auto recentJobs = obj->getProperty("recentJobIds"); recentJobs.isArray())
        for (const auto& value : *recentJobs.getArray())
            state.recentJobIds.add(value.toString());

    if (auto pendingRequests = obj->getProperty("pendingRequestIds"); pendingRequests.isArray())
        for (const auto& value : *pendingRequests.getArray())
            state.pendingRequestIds.add(value.toString());

    if (auto recentAssets = obj->getProperty("recentAssetIds"); recentAssets.isArray())
        for (const auto& value : *recentAssets.getArray())
            state.recentAssetIds.add(value.toString());

    return state;
}

void PluginStateStore::save(const PluginState& state) const
{
    juce::DynamicObject root;
    root.setProperty("discoveryCachePath", state.discoveryCachePath.getFullPathName());
    root.setProperty("mode", state.mode);
    root.setProperty("soundLoop", state.soundLoop);
    root.setProperty("bpmHint", state.bpmHint);
    root.setProperty("keyHint", state.keyHint);
    root.setProperty("lastSelectedOutputPath", state.lastSelectedOutputPath);
    root.setProperty("lastActiveJobId", state.lastActiveJobId);

    juce::Array<juce::var> recentJobs;
    for (const auto& id : state.recentJobIds)
        recentJobs.add(id);
    root.setProperty("recentJobIds", recentJobs);

    juce::Array<juce::var> pendingRequests;
    for (const auto& id : state.pendingRequestIds)
        pendingRequests.add(id);
    root.setProperty("pendingRequestIds", pendingRequests);

    juce::Array<juce::var> recentAssets;
    for (const auto& id : state.recentAssetIds)
        recentAssets.add(id);
    root.setProperty("recentAssetIds", recentAssets);

    path.getParentDirectory().createDirectory();
    path.replaceWithText(juce::JSON::toString(&root, true));
}
} // namespace suno::bridge
