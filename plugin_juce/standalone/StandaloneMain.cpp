#include <juce_gui_extra/juce_gui_extra.h>

#include "BridgeController.h"

class StandaloneClientComponent : public juce::Component,
                                  private juce::Button::Listener,
                                  private juce::Timer
{
public:
    StandaloneClientComponent()
        : controller(
              suno::bridge::PluginStateStore(
                  juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory)
                      .getChildFile("SunoStudio/standalone_state.json")),
              suno::bridge::ClientConfig())
    {
        prompt.setTextToShowWhenEmpty("Prompt", juce::Colours::grey);
        addAndMakeVisible(prompt);

        configureButton(connect, "Connect");
        configureButton(submitText, "Submit Text");
        configureButton(importAudio, "Import+Audio Job");
        configureButton(cancel, "Cancel");
        configureButton(preview, "Preview");
        configureButton(drag, "Drag");
        configureButton(reveal, "Reveal");

        status.setText("Disconnected", juce::dontSendNotification);
        addAndMakeVisible(status);

        addAndMakeVisible(outputs);
        outputs.onChange = [this]
        {
            if (outputs.getSelectedId() > 0)
                selected = juce::File(outputs.getItemText(outputs.getSelectedItemIndex()));
        };

        startTimerHz(4);
    }

    void resized() override
    {
        auto area = getLocalBounds().reduced(8);
        status.setBounds(area.removeFromTop(24));
        prompt.setBounds(area.removeFromTop(28));

        auto row = area.removeFromTop(30);
        connect.setBounds(row.removeFromLeft(90));
        submitText.setBounds(row.removeFromLeft(110));
        importAudio.setBounds(row.removeFromLeft(140));
        cancel.setBounds(row.removeFromLeft(90));
        preview.setBounds(row.removeFromLeft(80));
        drag.setBounds(row.removeFromLeft(80));
        reveal.setBounds(row.removeFromLeft(80));

        outputs.setBounds(area);
    }

private:
    void configureButton(juce::TextButton& b, const juce::String& text)
    {
        b.setButtonText(text);
        b.addListener(this);
        addAndMakeVisible(b);
    }

    void buttonClicked(juce::Button* b) override
    {
        juce::String error;
        if (b == &connect)
        {
            auto lockfile = juce::File::getSpecialLocation(juce::File::userHomeDirectory).getChildFile(".suno_studio/bridge.lock");
            if (! controller.connectWithDiscovery(lockfile, {}, error))
                controller.connectDev("127.0.0.1", 7071, "dev-shared-secret", error);
            status.setText(error.isEmpty() ? "Connected" : error, juce::dontSendNotification);
        }
        else if (b == &submitText)
        {
            juce::DynamicObject meta;
            meta.setProperty("surface", "standalone");
            controller.submitText(prompt.getText(), juce::var(&meta), error);
            status.setText(error.isEmpty() ? "Text submitted" : error, juce::dontSendNotification);
        }
        else if (b == &importAudio)
        {
            juce::FileChooser chooser("Select audio file");
            if (! chooser.browseForFileToOpen())
                return;
            juce::DynamicObject meta;
            meta.setProperty("surface", "standalone");
            controller.importAndSubmitAudio(chooser.getResult(), prompt.getText(), juce::var(&meta), error);
            status.setText(error.isEmpty() ? "Audio submitted" : error, juce::dontSendNotification);
        }
        else if (b == &cancel)
        {
            controller.cancelActive(error);
            status.setText(error.isEmpty() ? "Cancel requested" : error, juce::dontSendNotification);
        }
        else if (b == &preview)
        {
            selected.startAsProcess();
        }
        else if (b == &drag)
        {
            juce::SystemClipboard::copyTextToClipboard(selected.getFullPathName());
            status.setText("Copied output path for drag handoff", juce::dontSendNotification);
        }
        else if (b == &reveal)
        {
            selected.revealToUser();
        }
    }

    void timerCallback() override
    {
        juce::String error;
        if (controller.pollActive(error))
        {
            outputs.clear(juce::dontSendNotification);
            int i = 1;
            for (const auto& f : controller.getOutputFiles())
                outputs.addItem(f, i++);

            auto job = controller.getActiveJob();
            status.setText(job.status + " " + juce::String(job.progress), juce::dontSendNotification);
        }
    }

    suno::bridge::BridgeController controller;

    juce::Label status;
    juce::TextEditor prompt;
    juce::TextButton connect;
    juce::TextButton submitText;
    juce::TextButton importAudio;
    juce::TextButton cancel;
    juce::TextButton preview;
    juce::TextButton drag;
    juce::TextButton reveal;
    juce::ComboBox outputs;

    juce::File selected;
};

class StandaloneWindow : public juce::DocumentWindow
{
public:
    StandaloneWindow() : juce::DocumentWindow("Suno Studio Bridge Standalone",
                                              juce::Colours::darkgrey,
                                              DocumentWindow::allButtons)
    {
        setUsingNativeTitleBar(true);
        setContentOwned(new StandaloneClientComponent(), true);
        centreWithSize(900, 420);
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
    const juce::String getApplicationVersion() override { return "0.2.0"; }

    void initialise(const juce::String&) override { window.reset(new StandaloneWindow()); }
    void shutdown() override { window = nullptr; }

private:
    std::unique_ptr<StandaloneWindow> window;
};

START_JUCE_APPLICATION(StandaloneApp)
