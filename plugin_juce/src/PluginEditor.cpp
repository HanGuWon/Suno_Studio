#include "PluginProcessor.h"

#include "BridgeClientSurface.h"

class SunoStudioBridgeEditor : public juce::AudioProcessorEditor
{
public:
    explicit SunoStudioBridgeEditor(SunoStudioBridgeProcessor& p)
        : juce::AudioProcessorEditor(&p),
          surface(
              juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory)
                  .getChildFile("SunoStudio/plugin_client_state.json"),
              "plugin")
    {
        addAndMakeVisible(surface);
        setSize(1080, 680);
    }

    void resized() override
    {
        surface.setBounds(getLocalBounds());
    }

private:
    suno::bridge::BridgeClientSurface surface;
};

juce::AudioProcessorEditor* createSunoStudioBridgeEditor(SunoStudioBridgeProcessor& processor)
{
    return new SunoStudioBridgeEditor(processor);
}
