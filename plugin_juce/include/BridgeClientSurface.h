#pragma once

#include <juce_gui_extra/juce_gui_extra.h>

#include "BridgeController.h"

namespace suno::bridge
{
class BridgeClientSurface : public juce::Component,
                            public juce::FileDragAndDropTarget,
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
    void syncSelectedOutput();
    void updateOutputActions();
    bool revealSelectedOutput(juce::String& errorOut);
    bool dragSelectedOutputToDaw(juce::String& errorOut);
    bool hasPendingManualImport() const;
    bool isSupportedDropFile(const juce::File& file) const;
    RequestedOutputFamily guessedDropFamily(const juce::Array<juce::File>& files) const;
    void captureDroppedFiles(const juce::Array<juce::File>& files);
    void updateDropActions();
    juce::String pendingDropSummary() const;
    bool importPendingDroppedFiles(juce::String& errorOut);
    juce::File downloadsFolder() const;
    juce::Array<juce::File> collectDownloadCandidates(bool includeSeen);
    void seedSeenDownloadFiles();
    bool scanDownloadsForResultFiles(bool includeSeen, juce::String& errorOut);
    void updateDownloadWatchStatus();

    bool isInterestedInFileDrag(const juce::StringArray& files) override;
    void fileDragEnter(const juce::StringArray& files, int x, int y) override;
    void fileDragExit(const juce::StringArray& files) override;
    void filesDropped(const juce::StringArray& files, int x, int y) override;

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

    juce::Label dropLabel;
    juce::ComboBox dropFamily;
    juce::TextButton importDropped;
    juce::TextButton clearDropped;
    juce::Label downloadWatchLabel;
    juce::TextButton scanDownloads;
    juce::ToggleButton watchDownloads;
    juce::Label outputLabel;
    juce::ComboBox outputs;

    juce::Array<juce::File> mixFiles;
    juce::Array<juce::File> stemFiles;
    juce::Array<juce::File> tempoLockedStemFiles;
    juce::Array<juce::File> midiFiles;

    juce::File selected;
    juce::String lastUiError;
    juce::Array<juce::File> pendingDropFiles;
    RequestedOutputFamily pendingDropFamily { RequestedOutputFamily::Mix };
    bool externalFileDragActive { false };
    juce::StringArray seenDownloadPaths;
    int downloadWatchTick { 0 };
};
} // namespace suno::bridge
