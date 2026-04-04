#include "BridgeClientSurface.h"

namespace suno::bridge
{
BridgeClientSurface::BridgeClientSurface(juce::File stateFile, juce::String surface)
    : controller(PluginStateStore(std::move(stateFile)), ClientConfig()),
      surfaceName(std::move(surface))
{
    addAndMakeVisible(statusLabel);
    addAndMakeVisible(manualLabel);
    addAndMakeVisible(importedLabel);
    manualLabel.setText("Manual mode states: awaiting submission/result/importing", juce::dontSendNotification);
    importedLabel.setText("Imported deliverables: none", juce::dontSendNotification);

    prompt.setMultiLine(true);
    prompt.setTextToShowWhenEmpty("Prompt", juce::Colours::grey);
    addAndMakeVisible(prompt);

    providerMode.addItem("mock_suno", 1);
    providerMode.addItem("manual_suno", 2);
    providerMode.setSelectedId(controller.getState().providerMode == ProviderMode::ManualSuno ? 2 : 1);
    addAndMakeVisible(providerMode);

    mode.addItem("Song", 1);
    mode.addItem("Sound", 2);
    mode.addItem("Audio Prompt", 3);
    mode.setSelectedId(static_cast<int>(controller.getState().mode) + 1);
    addAndMakeVisible(mode);

    outputMix.setButtonText("mix");
    outputStems.setButtonText("stems");
    outputTempoLockedStems.setButtonText("tempo-locked stems");
    outputMidi.setButtonText("MIDI");
    for (auto* t : {&outputMix, &outputStems, &outputTempoLockedStems, &outputMidi, &soundOneShot, &soundLoop})
        addAndMakeVisible(*t);

    outputMix.setToggleState(true, juce::dontSendNotification);
    for (auto out : controller.getState().requestedOutputs)
    {
        outputMix.setToggleState(out == RequestedOutputFamily::Mix || outputMix.getToggleState(), juce::dontSendNotification);
        outputStems.setToggleState(out == RequestedOutputFamily::Stems || outputStems.getToggleState(), juce::dontSendNotification);
        outputTempoLockedStems.setToggleState(out == RequestedOutputFamily::TempoLockedStems || outputTempoLockedStems.getToggleState(), juce::dontSendNotification);
        outputMidi.setToggleState(out == RequestedOutputFamily::Midi || outputMidi.getToggleState(), juce::dontSendNotification);
    }

    soundOneShot.setButtonText("one-shot");
    soundOneShot.setToggleState(controller.getState().soundOneShot, juce::dontSendNotification);
    soundLoop.setButtonText("loop");
    soundLoop.setToggleState(controller.getState().soundLoop, juce::dontSendNotification);

    bpm.setInputRestrictions(3, "0123456789");
    bpm.setText(juce::String(controller.getState().bpmHint));
    key.setText(controller.getState().keyHint);
    addAndMakeVisible(bpm);
    addAndMakeVisible(key);

    configureButton(connect, "Connect");
    configureButton(connectDev, "Connect Dev");
    configureButton(submitText, "Submit Text Job");
    configureButton(importAudio, "Import + Submit Audio Job");
    configureButton(cancel, "Cancel Active Job");
    configureButton(fetchHandoff, "Prepare / Fetch Handoff");
    configureButton(revealHandoff, "Reveal Handoff Folder");
    configureButton(openInstructions, "Open Handoff Instructions");
    configureButton(importResults, "Import Suno Results");
    configureButton(preview, "Preview Result (disabled)");
    preview.setEnabled(false);
    configureButton(reveal, "Reveal Result");
    configureButton(drag, "Drag / copy result path");

    addAndMakeVisible(outputs);
    outputs.onChange = [this]
    {
        if (outputs.getSelectedId() <= 0)
            return;
        selected = juce::File(outputs.getItemText(outputs.getSelectedItemIndex()));
        controller.selectOutputFile(selected.getFullPathName());
    };

    if (controller.getState().lastSelectedOutputPath.isNotEmpty())
        selected = juce::File(controller.getState().lastSelectedOutputPath);

    updateControllerSettings();
    refreshStatus();
    startTimerHz(4);
}

BridgeClientSurface::~BridgeClientSurface()
{
}

void BridgeClientSurface::configureButton(juce::TextButton& button, const juce::String& text)
{
    button.setButtonText(text);
    addAndMakeVisible(button);
    button.addListener(this);
}

void BridgeClientSurface::updateControllerSettings()
{
    controller.setProviderMode(providerMode.getSelectedId() == 2 ? ProviderMode::ManualSuno : ProviderMode::MockSuno);
    controller.setMode(static_cast<ClientMode>(juce::jlimit(0, 2, mode.getSelectedId() - 1)));

    juce::Array<RequestedOutputFamily> requested;
    if (outputMix.getToggleState()) requested.add(RequestedOutputFamily::Mix);
    if (outputStems.getToggleState()) requested.add(RequestedOutputFamily::Stems);
    if (outputTempoLockedStems.getToggleState()) requested.add(RequestedOutputFamily::TempoLockedStems);
    if (outputMidi.getToggleState()) requested.add(RequestedOutputFamily::Midi);
    controller.setRequestedOutputs(requested);

    controller.setSoundOptions(soundOneShot.getToggleState(), soundLoop.getToggleState(), bpm.getText().getIntValue(), key.getText());
}

void BridgeClientSurface::refreshStatus()
{
    auto job = controller.getActiveJob();
    auto provider = toApiString(controller.getState().providerMode);
    auto stateText = controller.isConnected() ? "connected" : "disconnected";
    if (job.id.isNotEmpty())
        stateText << " | job=" << job.id << " | status=" << job.status << " | provider=" << provider;
    statusLabel.setText("[" + surfaceName + "] " + stateText, juce::dontSendNotification);
    if (lastActionMessage.isNotEmpty())
        statusLabel.setText(statusLabel.getText() + " | " + (lastActionWasError ? "error: " : "info: ") + lastActionMessage, juce::dontSendNotification);

    if (isManualWaitingState(job.status))
        manualLabel.setText("manual_suno: waiting state = " + job.status, juce::dontSendNotification);
    else if (job.status == "complete" && job.providerMode == ProviderMode::ManualSuno)
        manualLabel.setText("manual_suno: imported/complete", juce::dontSendNotification);
    else
        manualLabel.setText("Manual mode states: awaiting submission/result/importing", juce::dontSendNotification);

    importedLabel.setText("Imported deliverables: " + importedSummary(), juce::dontSendNotification);
}

void BridgeClientSurface::refreshOutputList()
{
    outputs.clear(juce::dontSendNotification);
    int i = 1;
    for (const auto& file : controller.getOutputFiles())
        outputs.addItem(file, i++);
    refreshStatus();
}

bool BridgeClientSurface::chooseAndAddFiles(juce::Array<juce::File>& target, const juce::String& title)
{
    juce::FileChooser chooser(title);
    if (chooser.browseForMultipleFilesToOpen())
    {
        target.addArray(chooser.getResults());
        return true;
    }
    return false;
}

int BridgeClientSurface::importedCount(const juce::String& familyKey) const
{
    auto imported = controller.getLastImportedFamilies();
    if (! imported.isObject())
        return 0;
    auto family = imported.getProperty(familyKey, juce::var());
    if (! family.isArray())
        return 0;
    return family.getArray()->size();
}

juce::String BridgeClientSurface::importedSummary() const
{
    return "mix=" + juce::String(importedCount("mix"))
        + ", stems=" + juce::String(importedCount("stems"))
        + ", tempoLockedStems=" + juce::String(importedCount("tempoLockedStems"))
        + ", midi=" + juce::String(importedCount("midi"));
}

bool BridgeClientSurface::shouldRequestFamily(RequestedOutputFamily family) const
{
    const auto requested = controller.getState().requestedOutputs;
    if (! requested.contains(family))
        return false;

    switch (family)
    {
        case RequestedOutputFamily::Mix: return importedCount("mix") == 0;
        case RequestedOutputFamily::Stems: return importedCount("stems") == 0;
        case RequestedOutputFamily::TempoLockedStems: return importedCount("tempoLockedStems") == 0;
        case RequestedOutputFamily::Midi: return importedCount("midi") == 0;
    }
    return false;
}

void BridgeClientSurface::setActionResult(const juce::String& text, bool isError)
{
    lastActionMessage = text;
    lastActionWasError = isError;
}

void BridgeClientSurface::buttonClicked(juce::Button* b)
{
    updateControllerSettings();
    juce::String error;

    if (b == &connect)
    {
        auto lockfile = juce::File::getSpecialLocation(juce::File::userHomeDirectory).getChildFile(".suno_studio/bridge.lock");
        if (! controller.connectWithDiscovery(lockfile, {}, error))
            setActionResult(error, true);
        else
            setActionResult(error.isNotEmpty() ? error : "Connected via discovery", false);
    }
    else if (b == &connectDev)
    {
        if (! controller.connectDev("127.0.0.1", 7071, "dev-shared-secret", error))
            setActionResult(error, true);
        else
            setActionResult(error.isNotEmpty() ? error : "Connected via dev endpoint", false);
    }
    else if (b == &submitText)
    {
        if (! controller.submitText(prompt.getText(), error))
            setActionResult(error, true);
        else
            setActionResult("Submitted text job", false);
    }
    else if (b == &importAudio)
    {
        juce::FileChooser chooser("Select local audio prompt file");
        if (chooser.browseForFileToOpen())
        {
            if (! controller.importAndSubmitAudio(chooser.getResult(), prompt.getText(), error))
                setActionResult(error, true);
            else
                setActionResult("Submitted audio prompt job", false);
        }
    }
    else if (b == &cancel)
    {
        if (! controller.cancelActive(error))
            setActionResult(error, true);
        else
            setActionResult("Cancel requested", false);
    }
    else if (b == &fetchHandoff)
    {
        if (! controller.fetchHandoff(error))
            setActionResult(error, true);
        else
            setActionResult("Handoff fetched", false);
    }
    else if (b == &revealHandoff)
    {
        if (! controller.revealHandoffFolder(error))
            setActionResult(error, true);
        else
            setActionResult("Handoff folder revealed", false);
    }
    else if (b == &openInstructions)
    {
        if (! controller.openHandoffInstructions(error))
            setActionResult(error, true);
        else
            setActionResult("Opened handoff instructions", false);
    }
    else if (b == &importResults)
    {
        mixFiles.clear(); stemFiles.clear(); tempoLockedStemFiles.clear(); midiFiles.clear();
        if (shouldRequestFamily(RequestedOutputFamily::Mix))
            chooseAndAddFiles(mixFiles, "Pick mix result file(s)");
        if (shouldRequestFamily(RequestedOutputFamily::Stems))
            chooseAndAddFiles(stemFiles, "Pick stem result file(s)");
        if (shouldRequestFamily(RequestedOutputFamily::TempoLockedStems))
            chooseAndAddFiles(tempoLockedStemFiles, "Pick tempo-locked stem file(s)");
        if (shouldRequestFamily(RequestedOutputFamily::Midi))
            chooseAndAddFiles(midiFiles, "Pick MIDI file(s)");

        if (mixFiles.isEmpty() && stemFiles.isEmpty() && tempoLockedStemFiles.isEmpty() && midiFiles.isEmpty())
        {
            setActionResult("No files selected. Manual complete was not sent.", false);
            refreshOutputList();
            return;
        }

        ManualCompleteFiles completion;
        completion.mixFiles = mixFiles;
        completion.stemFiles = stemFiles;
        completion.tempoLockedStemFiles = tempoLockedStemFiles;
        completion.midiFiles = midiFiles;
        if (! controller.manualCompleteActive(completion, error))
            setActionResult(error, true);
        else
            setActionResult("Imported selected deliverables", false);
    }
    else if (b == &preview)
    {
        setActionResult("Preview is disabled in this milestone (use reveal/open externally).", false);
    }
    else if (b == &reveal)
    {
        if (selected.existsAsFile())
        {
            selected.revealToUser();
            setActionResult("Revealed selected result.", false);
        }
        else
            setActionResult("No selected result file to reveal.", true);
    }
    else if (b == &drag)
    {
        if (selected.existsAsFile())
        {
            performExternalDragDropOfFiles({ selected.getFullPathName() }, false);
            juce::SystemClipboard::copyTextToClipboard(selected.getFullPathName());
            setActionResult("Copied output path and initiated drag.", false);
        }
        else
            setActionResult("No selected result file for drag/copy.", true);
    }

    refreshOutputList();
}

void BridgeClientSurface::timerCallback()
{
    juce::String error;
    if (! controller.pollActive(error) && error.isNotEmpty())
        setActionResult("Poll warning: " + error, true);
    refreshOutputList();
}

void BridgeClientSurface::resized()
{
    auto area = getLocalBounds().reduced(8);
    statusLabel.setBounds(area.removeFromTop(22));
    manualLabel.setBounds(area.removeFromTop(20));
    importedLabel.setBounds(area.removeFromTop(20));

    auto providerRow = area.removeFromTop(24);
    providerMode.setBounds(providerRow.removeFromLeft(180));
    mode.setBounds(providerRow.removeFromLeft(180));
    outputMix.setBounds(providerRow.removeFromLeft(90));
    outputStems.setBounds(providerRow.removeFromLeft(90));
    outputTempoLockedStems.setBounds(providerRow.removeFromLeft(150));
    outputMidi.setBounds(providerRow.removeFromLeft(80));

    auto soundRow = area.removeFromTop(24);
    soundOneShot.setBounds(soundRow.removeFromLeft(100));
    soundLoop.setBounds(soundRow.removeFromLeft(80));
    bpm.setBounds(soundRow.removeFromLeft(60));
    key.setBounds(soundRow.removeFromLeft(70));

    prompt.setBounds(area.removeFromTop(90));

    auto row1 = area.removeFromTop(28);
    connect.setBounds(row1.removeFromLeft(90));
    connectDev.setBounds(row1.removeFromLeft(100));
    submitText.setBounds(row1.removeFromLeft(130));
    importAudio.setBounds(row1.removeFromLeft(170));
    cancel.setBounds(row1.removeFromLeft(130));

    auto row2 = area.removeFromTop(28);
    fetchHandoff.setBounds(row2.removeFromLeft(180));
    revealHandoff.setBounds(row2.removeFromLeft(160));
    openInstructions.setBounds(row2.removeFromLeft(180));
    importResults.setBounds(row2.removeFromLeft(160));

    auto row3 = area.removeFromTop(28);
    preview.setBounds(row3.removeFromLeft(130));
    reveal.setBounds(row3.removeFromLeft(120));
    drag.setBounds(row3.removeFromLeft(190));

    outputs.setBounds(area);
}
} // namespace suno::bridge
