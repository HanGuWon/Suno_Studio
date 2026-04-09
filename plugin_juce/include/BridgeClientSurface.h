#pragma once

#include <juce_gui_extra/juce_gui_extra.h>

#include "BridgeController.h"

namespace suno::bridge
{
class BridgeClientSurface : public juce::Component,
                            private juce::Button::Listener,
                            private juce::Timer,
                            private juce::DragAndDropContainer
{
public:
    BridgeClientSurface(juce::File stateFile, juce::String surfaceName);
    ~BridgeClientSurface() override;

    void resized() override;

private:
    void configureButton(juce::TextButton& button, const juce::String& text);
    void updateControllerSettings();
    void refreshStatus();
    void refreshOutputList();
    bool shouldPromptForFamily(RequestedOutputFamily family) const;
    bool hasImportedFamily(RequestedOutputFamily family) const;
    bool isFamilyRequested(RequestedOutputFamily family) const;
    juce::String manualImportSummary() const;
    void chooseAndAddFiles(juce::Array<juce::File>& target, const juce::String& title);

    void buttonClicked(juce::Button* button) override;
    void timerCallback() override;

    BridgeController controller;
    juce::String surfaceName;

    juce::Label statusLabel;
    juce::Label manualLabel;
    juce::TextEditor prompt;
    juce::ComboBox providerMode;
    juce::ComboBox mode;
    juce::ToggleButton outputMix;
    juce::ToggleButton outputStems;
    juce::ToggleButton outputTempoLockedStems;
    juce::ToggleButton outputMidi;
    juce::ToggleButton soundOneShot;
    juce::ToggleButton soundLoop;
    juce::TextEditor bpm;
    juce::TextEditor key;

    juce::TextButton connect;
    juce::TextButton connectDev;
    juce::TextButton submitText;
    juce::TextButton importAudio;
    juce::TextButton cancel;
    juce::TextButton fetchHandoff;
    juce::TextButton revealHandoff;
    juce::TextButton openInstructions;
    juce::TextButton importResults;
    juce::TextButton preview;
    juce::TextButton reveal;
    juce::TextButton drag;

    juce::ComboBox outputs;

    juce::Array<juce::File> mixFiles;
    juce::Array<juce::File> stemFiles;
    juce::Array<juce::File> tempoLockedStemFiles;
    juce::Array<juce::File> midiFiles;

    juce::File selected;
    juce::String lastUiError;
};
} // namespace suno::bridge
