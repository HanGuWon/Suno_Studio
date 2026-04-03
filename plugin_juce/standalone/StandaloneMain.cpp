#include <juce_gui_extra/juce_gui_extra.h>

#include "BridgeClientSurface.h"

class StandaloneWindow : public juce::DocumentWindow
{
public:
    StandaloneWindow() : juce::DocumentWindow("Suno Studio Bridge Standalone",
                                              juce::Colours::darkgrey,
                                              DocumentWindow::allButtons)
    {
        setUsingNativeTitleBar(true);
        setContentOwned(new suno::bridge::BridgeClientSurface(
                            juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory)
                                .getChildFile("SunoStudio/standalone_state.json"),
                            "standalone"),
                        true);
        centreWithSize(1120, 720);
        setVisible(true);
    }

    void closeButtonPressed() override
    {
        juce::JUCEApplication::getInstance()->systemRequestedQuit();
    }
};

class StandaloneApp : public juce::JUCEApplication
{
public:
    const juce::String getApplicationName() override { return "SunoStudioBridgeStandalone"; }
    const juce::String getApplicationVersion() override { return "0.3.0"; }

    void initialise(const juce::String&) override { window.reset(new StandaloneWindow()); }
    void shutdown() override { window = nullptr; }

private:
    std::unique_ptr<StandaloneWindow> window;
};

START_JUCE_APPLICATION(StandaloneApp)
