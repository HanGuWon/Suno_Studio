#include "BridgeDiscovery.h"

namespace suno::bridge
{
BridgeDiscovery::BridgeDiscovery(juce::File lockfilePath)
    : lockfile(std::move(lockfilePath))
{
}

DiscoveryInfo BridgeDiscovery::discover() const
{
    DiscoveryInfo info;

    if (! lockfile.existsAsFile())
        return info;

    const auto parsed = juce::JSON::parse(lockfile);
    if (! parsed.isObject())
        return info;

    auto* object = parsed.getDynamicObject();
    info.host = object->getProperty("host").toString();
    info.port = static_cast<int>(object->getProperty("port"));

    if (auto protocol = object->getProperty("protocol"); protocol.isObject())
    {
        auto* protocolObj = protocol.getDynamicObject();
        info.protocolMin = protocolObj->getProperty("min_supported").toString();
        info.protocolMax = protocolObj->getProperty("max_supported").toString();
    }

    if (auto auth = object->getProperty("auth"); auth.isObject())
        info.hmacRequired = static_cast<bool>(auth.getDynamicObject()->getProperty("hmac"));

    return info;
}
} // namespace suno::bridge
