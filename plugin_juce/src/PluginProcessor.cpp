#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_audio_utils/juce_audio_utils.h>

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
        : juce::AudioProcessorEditor(&p), processor(p)
    {
        formatManager.registerBasicFormats();

        setSize(760, 560);
        configureLabel(statusLabel, "Bridge: disconnected (scaffold)");
        configureLabel(hostModeLabel, "Host mode: Generic Drag / REAPER Assisted / ARA Planned");

        modeBox.addItem("Song", 1);
        modeBox.addItem("Sound", 2);
        modeBox.addItem("Audio Prompt", 3);
        modeBox.setSelectedId(1);
        addAndMakeVisible(modeBox);

        promptEditor.setMultiLine(true);
        promptEditor.setTextToShowWhenEmpty("Type prompt...", juce::Colours::grey);
        addAndMakeVisible(promptEditor);

        configureButton(submitButton, "Submit Text Job");
        configureButton(cancelButton, "Cancel Active Job");
        configureButton(importButton, "Import Audio Prompt");
        configureButton(selectResultButton, "Select Result File");
        configureButton(previewButton, "Preview/Stop");
        configureButton(dragButton, "Drag Result Out");
        configureButton(revealButton, "Reveal In Folder");

        addAndMakeVisible(jobList);
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
        submitButton.setBounds(row1.removeFromLeft(150));
        cancelButton.setBounds(row1.removeFromLeft(150));
        importButton.setBounds(row1.removeFromLeft(170));

        auto row2 = area.removeFromTop(30);
        selectResultButton.setBounds(row2.removeFromLeft(150));
        previewButton.setBounds(row2.removeFromLeft(120));
        dragButton.setBounds(row2.removeFromLeft(130));
        revealButton.setBounds(row2.removeFromLeft(130));

        jobList.setBounds(area);
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
        if (button == &submitButton)
            statusLabel.setText("Text job submitted (scaffold)", juce::dontSendNotification);
        else if (button == &cancelButton)
            statusLabel.setText("Cancel requested (scaffold)", juce::dontSendNotification);
        else if (button == &importButton)
            importAudioPrompt();
        else if (button == &selectResultButton)
            selectResultFile();
        else if (button == &previewButton)
            togglePreview();
        else if (button == &dragButton)
            dragSelectedResult();
        else if (button == &revealButton)
            revealSelectedResult();
    }

    void timerCallback() override
    {
        // TODO: poll bridge job status and refresh list from async runtime endpoints.
    }

    void importAudioPrompt()
    {
        juce::FileChooser chooser("Select local audio prompt file");
        if (chooser.browseForFileToOpen())
            statusLabel.setText("Audio prompt selected: " + chooser.getResult().getFileName(), juce::dontSendNotification);
    }

    void selectResultFile()
    {
        juce::FileChooser chooser("Select generated result file");
        if (! chooser.browseForFileToOpen())
            return;

        selectedResultFile = chooser.getResult();
        statusLabel.setText("Selected result: " + selectedResultFile.getFileName(), juce::dontSendNotification);
        loadPreview(selectedResultFile);
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
        {
            statusLabel.setText("No selected result file", juce::dontSendNotification);
            return;
        }

        if (transportSource.isPlaying())
        {
            transportSource.stop();
            statusLabel.setText("Preview stopped", juce::dontSendNotification);
            return;
        }

        transportSource.setPosition(0.0);
        transportSource.start();
        statusLabel.setText("Preview started", juce::dontSendNotification);
    }

    void dragSelectedResult()
    {
        if (! selectedResultFile.existsAsFile())
        {
            statusLabel.setText("No selected result file", juce::dontSendNotification);
            return;
        }

        const juce::StringArray files { selectedResultFile.getFullPathName() };
        performExternalDragDropOfFiles(files, false);
        statusLabel.setText("External drag started", juce::dontSendNotification);
    }

    void revealSelectedResult()
    {
        if (selectedResultFile.existsAsFile())
            selectedResultFile.revealToUser();
    }

    SunoStudioBridgeProcessor& processor;

    juce::Label statusLabel;
    juce::Label hostModeLabel;
    juce::ComboBox modeBox;
    juce::TextEditor promptEditor;
    juce::TextButton submitButton;
    juce::TextButton cancelButton;
    juce::TextButton importButton;
    juce::TextButton selectResultButton;
    juce::TextButton previewButton;
    juce::TextButton dragButton;
    juce::TextButton revealButton;
    juce::ListBox jobList;

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
