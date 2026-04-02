#pragma once

#include "BridgeModels.h"

namespace suno::bridge
{
class BridgeDiscovery
{
public:
    explicit BridgeDiscovery(juce::File lockfilePath);
    DiscoveryInfo discover() const;

private:
    juce::File lockfile;
};
} // namespace suno::bridge
