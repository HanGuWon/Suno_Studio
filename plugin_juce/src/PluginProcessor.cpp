#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_audio_utils/juce_audio_utils.h>

#include "BridgeController.h"

class SunoStudioBridgeProcessor : public juce::AudioProcessor
{
public:
    SunoStudioBridgeProcessor() = default;

    const juce::String getName() const override { return "SunoStudioBridge"; }
    void prepareToPlay(double, int) override {}
    void releaseResources() override {}
    bool isBusesLayoutSupported(const BusesLayout&) const override { return true; }
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override {}

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    double getTailLengthSeconds() const override { return 0.0; }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return {}; }
    void changeProgramName(int, const juce::String&) override {}

    void getStateInformation(juce::MemoryBlock&) override {}
    void setStateInformation(const void*, int) override {}
};

class SunoStudioBridgeEditor : public juce::AudioProcessorEditor,
                               private juce::Button::Listener,
                               private juce::Timer,
                               private juce::DragAndDropContainer
{
public:
    explicit SunoStudioBridgeEditor(SunoStudioBridgeProcessor& p)
        : juce::AudioProcessorEditor(&p),
          processor(p),
          controller(
              suno::bridge::PluginStateStore(
                  juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory)
                      .getChildFile("SunoStudio/plugin_client_state.json")),
              suno::bridge::ClientConfig())
    {
        formatManager.registerBasicFormats();

        setSize(840, 600);
        configureLabel(statusLabel, "Bridge: disconnected");
        configureLabel(hostModeLabel, "Host mode: Generic Drag / REAPER Assisted / ARA Planned");

        modeBox.addItem("Song", 1);
        modeBox.addItem("Sound", 2);
        modeBox.addItem("Audio Prompt", 3);
        modeBox.setSelectedId(1);
        addAndMakeVisible(modeBox);

        promptEditor.setMultiLine(true);
        promptEditor.setTextToShowWhenEmpty("Type prompt...", juce::Colours::grey);
        addAndMakeVisible(promptEditor);

        configureButton(connectButton, "Connect (Discovery)");
        configureButton(devConnectButton, "Connect Dev");
        configureButton(submitButton, "Submit Text Job");
        configureButton(cancelButton, "Cancel Active Job");
        configureButton(importButton, "Import + Submit Audio Job");
        configureButton(previewButton, "Preview/Stop");
        configureButton(dragButton, "Drag Selected Output");
        configureButton(revealButton, "Reveal Output");
        configureButton(copyPathButton, "Copy Output Path");

        addAndMakeVisible(outputList);
        outputList.onChange = [this]
        {
            if (outputList.getSelectedId() > 0)
            {
                auto path = outputList.getItemText(outputList.getSelectedItemIndex());
                controller.selectOutputFile(path);
                selectedResultFile = juce::File(path);
                loadPreview(selectedResultFile);
            }
        };

        startTimerHz(4);
    }

    ~SunoStudioBridgeEditor() override
    {
        transportSource.stop();
        transportSource.setSource(nullptr);
        readerSource.reset();
    }

    void resized() override
    {
        auto area = getLocalBounds().reduced(10);
        statusLabel.setBounds(area.removeFromTop(24));
        hostModeLabel.setBounds(area.removeFromTop(20));
        modeBox.setBounds(area.removeFromTop(28));
        promptEditor.setBounds(area.removeFromTop(120));

        auto row1 = area.removeFromTop(30);
        connectButton.setBounds(row1.removeFromLeft(150));
        devConnectButton.setBounds(row1.removeFromLeft(120));
        submitButton.setBounds(row1.removeFromLeft(150));
        cancelButton.setBounds(row1.removeFromLeft(140));

        auto row2 = area.removeFromTop(30);
        importButton.setBounds(row2.removeFromLeft(220));
        previewButton.setBounds(row2.removeFromLeft(120));
        dragButton.setBounds(row2.removeFromLeft(170));
        revealButton.setBounds(row2.removeFromLeft(130));
        copyPathButton.setBounds(row2.removeFromLeft(120));

        outputList.setBounds(area);
    }

private:
    void configureButton(juce::TextButton& button, const juce::String& text)
    {
        button.setButtonText(text);
        addAndMakeVisible(button);
        button.addListener(this);
    }

    void configureLabel(juce::Label& label, const juce::String& text)
    {
        addAndMakeVisible(label);
        label.setText(text, juce::dontSendNotification);
    }

    void buttonClicked(juce::Button* button) override
    {
        if (button == &connectButton)
            connectDiscovery();
        else if (button == &devConnectButton)
            connectDev();
        else if (button == &submitButton)
            submitText();
        else if (button == &cancelButton)
            cancelActive();
        else if (button == &importButton)
            importAndSubmitAudio();
        else if (button == &previewButton)
            togglePreview();
        else if (button == &dragButton)
            dragSelectedResult();
        else if (button == &revealButton)
            revealSelectedResult();
        else if (button == &copyPathButton)
            copyOutputPath();
    }

    void timerCallback() override
    {
        juce::String error;
        if (controller.pollActive(error))
            refreshOutputList();
    }

    void connectDiscovery()
    {
        auto lockfile = juce::File::getSpecialLocation(juce::File::userHomeDirectory).getChildFile(".suno_studio/bridge.lock");
        juce::String error;
        if (controller.connectWithDiscovery(lockfile, {}, error))
            statusLabel.setText("Bridge connected (discovery)", juce::dontSendNotification);
        else
            statusLabel.setText("Connect failed: " + error, juce::dontSendNotification);
    }

    void connectDev()
    {
        juce::String error;
        if (controller.connectDev("127.0.0.1", 7071, "dev-shared-secret", error))
            statusLabel.setText("Bridge connected (dev)", juce::dontSendNotification);
        else
            statusLabel.setText("Dev connect failed: " + error, juce::dontSendNotification);
    }

    void submitText()
    {
        juce::String error;
        juce::DynamicObject metadata;
        metadata.setProperty("clientMode", modeBox.getText());
        if (controller.submitText(promptEditor.getText(), juce::var(&metadata), error))
            statusLabel.setText("Text job submitted", juce::dontSendNotification);
        else
            statusLabel.setText("Submit failed: " + error, juce::dontSendNotification);
    }

    void importAndSubmitAudio()
    {
        juce::FileChooser chooser("Select local audio prompt file");
        if (! chooser.browseForFileToOpen())
            return;

        juce::String error;
        juce::DynamicObject metadata;
        metadata.setProperty("clientMode", "audio_prompt");
        if (controller.importAndSubmitAudio(chooser.getResult(), promptEditor.getText(), juce::var(&metadata), error))
            statusLabel.setText("Audio job submitted", juce::dontSendNotification);
        else
            statusLabel.setText("Audio submit failed: " + error, juce::dontSendNotification);
    }

    void cancelActive()
    {
        juce::String error;
        if (controller.cancelActive(error))
            statusLabel.setText("Cancel requested", juce::dontSendNotification);
        else
            statusLabel.setText("Cancel failed: " + error, juce::dontSendNotification);
    }

    void refreshOutputList()
    {
        outputList.clear(juce::dontSendNotification);
        int idx = 1;
        for (const auto& file : controller.getOutputFiles())
            outputList.addItem(file, idx++);

        auto active = controller.getActiveJob();
        statusLabel.setText("Job " + active.id + " | " + active.status + " | " + juce::String(active.progress), juce::dontSendNotification);
    }

    void loadPreview(const juce::File& file)
    {
        auto* reader = formatManager.createReaderFor(file);
        if (reader == nullptr)
            return;

        readerSource.reset(new juce::AudioFormatReaderSource(reader, true));
        transportSource.setSource(readerSource.get(), 0, nullptr, reader->sampleRate);
    }

    void togglePreview()
    {
        if (! selectedResultFile.existsAsFile())
            return;

        if (transportSource.isPlaying())
            transportSource.stop();
        else
        {
            transportSource.setPosition(0.0);
            transportSource.start();
        }
    }

    void dragSelectedResult()
    {
        if (! selectedResultFile.existsAsFile())
            return;
        performExternalDragDropOfFiles({ selectedResultFile.getFullPathName() }, false);
    }

    void revealSelectedResult()
    {
        if (selectedResultFile.existsAsFile())
            selectedResultFile.revealToUser();
    }

    void copyOutputPath()
    {
        if (selectedResultFile.existsAsFile())
            juce::SystemClipboard::copyTextToClipboard(selectedResultFile.getFullPathName());
    }

    SunoStudioBridgeProcessor& processor;
    suno::bridge::BridgeController controller;

    juce::Label statusLabel;
    juce::Label hostModeLabel;
    juce::ComboBox modeBox;
    juce::TextEditor promptEditor;
    juce::TextButton connectButton;
    juce::TextButton devConnectButton;
    juce::TextButton submitButton;
    juce::TextButton cancelButton;
    juce::TextButton importButton;
    juce::TextButton previewButton;
    juce::TextButton dragButton;
    juce::TextButton revealButton;
    juce::TextButton copyPathButton;
    juce::ComboBox outputList;

    juce::File selectedResultFile;
    juce::AudioFormatManager formatManager;
    juce::AudioTransportSource transportSource;
    std::unique_ptr<juce::AudioFormatReaderSource> readerSource;
};

juce::AudioProcessorEditor* SunoStudioBridgeProcessor::createEditor()
{
    return new SunoStudioBridgeEditor(*this);
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new SunoStudioBridgeProcessor();
}
