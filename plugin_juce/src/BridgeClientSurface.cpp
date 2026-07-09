#include "BridgeClientSurface.h"

namespace suno::bridge
{
namespace
{
juce::String importedDeliverablesKey(RequestedOutputFamily family)
{
    switch (family)
    {
        case RequestedOutputFamily::Mix: return "mix";
        case RequestedOutputFamily::Stems: return "stems";
        case RequestedOutputFamily::TempoLockedStems: return "tempoLockedStems";
        case RequestedOutputFamily::Midi: return "midi";
    }

    return "mix";
}

juce::String requestedDeliverablesKey(RequestedOutputFamily family)
{
    switch (family)
    {
        case RequestedOutputFamily::Mix: return "mix";
        case RequestedOutputFamily::Stems: return "stems";
        case RequestedOutputFamily::TempoLockedStems: return "tempo_locked_stems";
        case RequestedOutputFamily::Midi: return "midi";
    }

    return "mix";
}
juce::String requestedDeliverablesCamelKey(RequestedOutputFamily family)
{
    switch (family)
    {
        case RequestedOutputFamily::Mix: return "mix";
        case RequestedOutputFamily::Stems: return "stems";
        case RequestedOutputFamily::TempoLockedStems: return "tempoLockedStems";
        case RequestedOutputFamily::Midi: return "midi";
    }

    return "mix";
}

juce::String shortOutputName(const juce::File& file)
{
    if (! file.existsAsFile())
        return "No output selected";

    return file.getFileName();
}

juce::String familyLabel(RequestedOutputFamily family)
{
    switch (family)
    {
        case RequestedOutputFamily::Mix: return "mix";
        case RequestedOutputFamily::Stems: return "stems";
        case RequestedOutputFamily::TempoLockedStems: return "tempo-locked stems";
        case RequestedOutputFamily::Midi: return "MIDI";
    }

    return "mix";
}

int familyComboId(RequestedOutputFamily family)
{
    switch (family)
    {
        case RequestedOutputFamily::Mix: return 1;
        case RequestedOutputFamily::Stems: return 2;
        case RequestedOutputFamily::TempoLockedStems: return 3;
        case RequestedOutputFamily::Midi: return 4;
    }

    return 1;
}

RequestedOutputFamily familyFromComboId(int selectedId)
{
    switch (selectedId)
    {
        case 2: return RequestedOutputFamily::Stems;
        case 3: return RequestedOutputFamily::TempoLockedStems;
        case 4: return RequestedOutputFamily::Midi;
        default: return RequestedOutputFamily::Mix;
    }
}

bool isAudioExtension(const juce::File& file)
{
    const auto ext = file.getFileExtension().toLowerCase();
    return ext == ".wav"
        || ext == ".wave"
        || ext == ".mp3"
        || ext == ".aif"
        || ext == ".aiff"
        || ext == ".flac"
        || ext == ".ogg"
        || ext == ".m4a"
        || ext == ".aac"
        || ext == ".opus"
        || ext == ".wma";
}

bool isMidiExtension(const juce::File& file)
{
    const auto ext = file.getFileExtension().toLowerCase();
    return ext == ".mid" || ext == ".midi";
}

bool hasStemNameHint(const juce::String& lowerName)
{
    return lowerName.contains("stem")
        || lowerName.contains("vocal")
        || lowerName.contains("drum")
        || lowerName.contains("bass")
        || lowerName.contains("guitar")
        || lowerName.contains("instrument")
        || lowerName.contains("piano")
        || lowerName.contains("synth")
        || lowerName.contains("lead")
        || lowerName.contains("backing")
        || lowerName.contains("harmony");
}

bool hasTempoNameHint(const juce::String& lowerName)
{
    return lowerName.contains("tempo")
        || lowerName.contains("locked")
        || lowerName.contains("bpm");
}
}

BridgeClientSurface::BridgeClientSurface(juce::File stateFile, juce::String surface)
    : controller(PluginStateStore(std::move(stateFile)), ClientConfig()),
      surfaceName(std::move(surface))
{
    addAndMakeVisible(statusLabel);
    addAndMakeVisible(manualLabel);
    manualLabel.setText("Manual mode states: awaiting submission/result/importing | preview disabled", juce::dontSendNotification);

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
    configureButton(preview, "Preview Unavailable");
    preview.setEnabled(false);
    configureButton(reveal, "Reveal Result");
    configureButton(drag, "Drag Selected Output");

    dropFamily.addItem("mix", familyComboId(RequestedOutputFamily::Mix));
    dropFamily.addItem("stems", familyComboId(RequestedOutputFamily::Stems));
    dropFamily.addItem("tempo-locked stems", familyComboId(RequestedOutputFamily::TempoLockedStems));
    dropFamily.addItem("MIDI", familyComboId(RequestedOutputFamily::Midi));
    dropFamily.setSelectedId(familyComboId(pendingDropFamily));
    dropFamily.onChange = [this]
    {
        pendingDropFamily = familyFromComboId(dropFamily.getSelectedId());
        updateDropActions();
    };
    addAndMakeVisible(dropLabel);
    addAndMakeVisible(dropFamily);
    configureButton(importDropped, "Import Dropped");
    configureButton(clearDropped, "Clear Dropped");

    addAndMakeVisible(downloadWatchLabel);
    configureButton(scanDownloads, "Scan Downloads");
    watchDownloads.setButtonText("Watch Downloads");
    watchDownloads.onClick = [this]
    {
        if (watchDownloads.getToggleState())
            seedSeenDownloadFiles();
        updateDownloadWatchStatus();
    };
    addAndMakeVisible(watchDownloads);

    addAndMakeVisible(outputLabel);
    addAndMakeVisible(outputs);
    outputs.onChange = [this]
    {
        if (outputs.getSelectedId() <= 0)
            return;
        selected = juce::File(outputs.getItemText(outputs.getSelectedItemIndex()));
        controller.selectOutputFile(selected.getFullPathName());
        updateOutputActions();
    };

    if (controller.getState().lastSelectedOutputPath.isNotEmpty())
        selected = juce::File(controller.getState().lastSelectedOutputPath);

    updateControllerSettings();
    updateOutputActions();
    updateDropActions();
    updateDownloadWatchStatus();
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
    juce::String stateText = controller.isConnected() ? "connected" : "disconnected";
    if (job.id.isNotEmpty())
        stateText << " | job=" << job.id << " | status=" << job.status << " | provider=" << provider;
    if (lastUiError.isNotEmpty())
        stateText << " | error=" << lastUiError;
    if (externalFileDragActive)
        stateText << " | file drop ready";
    statusLabel.setText("[" + surfaceName + "] " + stateText, juce::dontSendNotification);

    if (isManualWaitingState(job.status))
        manualLabel.setText("manual_suno: waiting state = " + job.status + " | " + manualImportSummary() + " | preview disabled", juce::dontSendNotification);
    else if (job.status == "complete" && job.providerMode == ProviderMode::ManualSuno)
        manualLabel.setText("manual_suno: imported/complete | " + manualImportSummary() + " | preview disabled", juce::dontSendNotification);
    else
        manualLabel.setText("Manual mode states: awaiting submission/result/importing | " + manualImportSummary() + " | preview disabled", juce::dontSendNotification);
}

void BridgeClientSurface::refreshOutputList()
{
    outputs.clear(juce::dontSendNotification);
    int i = 1;
    for (const auto& file : controller.getOutputFiles())
        outputs.addItem(file, i++);
    syncSelectedOutput();
    updateOutputActions();
    updateDropActions();
    refreshStatus();
}

void BridgeClientSurface::syncSelectedOutput()
{
    const auto& files = controller.getOutputFiles();
    if (files.isEmpty())
    {
        selected = {};
        outputs.setSelectedId(0, juce::dontSendNotification);
        return;
    }

    auto desired = selected.existsAsFile() ? selected : juce::File(controller.getState().lastSelectedOutputPath);
    if (! desired.existsAsFile())
        desired = juce::File(files[0]);

    int selectedId = 0;
    for (int i = 0; i < files.size(); ++i)
    {
        if (juce::File(files[i]) == desired)
        {
            selectedId = i + 1;
            break;
        }
    }

    if (selectedId == 0)
    {
        desired = juce::File(files[0]);
        selectedId = 1;
    }

    selected = desired;
    outputs.setSelectedId(selectedId, juce::dontSendNotification);
    if (controller.getState().lastSelectedOutputPath != selected.getFullPathName())
        controller.selectOutputFile(selected.getFullPathName());
}

void BridgeClientSurface::updateOutputActions()
{
    const auto hasOutput = selected.existsAsFile();
    outputLabel.setText("Output: " + shortOutputName(selected), juce::dontSendNotification);
    reveal.setEnabled(hasOutput);
    drag.setEnabled(hasOutput);
}

void BridgeClientSurface::updateDropActions()
{
    dropLabel.setText(pendingDropSummary(), juce::dontSendNotification);
    const auto hasDrop = ! pendingDropFiles.isEmpty();
    dropFamily.setEnabled(hasDrop);
    importDropped.setEnabled(hasDrop && hasPendingManualImport());
    clearDropped.setEnabled(hasDrop);
}

void BridgeClientSurface::chooseAndAddFiles(juce::Array<juce::File>& target, const juce::String& title)
{
    juce::FileChooser chooser(title);
    if (chooser.browseForMultipleFilesToOpen())
        target.addArray(chooser.getResults());
}

void BridgeClientSurface::buttonClicked(juce::Button* b)
{
    updateControllerSettings();
    juce::String error;

    if (b == &connect)
    {
        auto lockfile = juce::File::getSpecialLocation(juce::File::userHomeDirectory).getChildFile(".suno_studio/bridge.lock");
        if (controller.connectWithDiscovery(lockfile, {}, error))
            lastUiError.clear();
    }
    else if (b == &connectDev)
    {
        if (controller.connectDev("127.0.0.1", 7071, "dev-shared-secret", error))
            lastUiError.clear();
    }
    else if (b == &submitText)
    {
        controller.submitText(prompt.getText(), error);
    }
    else if (b == &importAudio)
    {
        juce::FileChooser chooser("Select local audio prompt file");
        if (chooser.browseForFileToOpen())
            controller.importAndSubmitAudio(chooser.getResult(), prompt.getText(), error);
    }
    else if (b == &cancel)
    {
        controller.cancelActive(error);
    }
    else if (b == &fetchHandoff)
    {
        controller.fetchHandoff(error);
    }
    else if (b == &revealHandoff)
    {
        controller.revealHandoffFolder(error);
    }
    else if (b == &openInstructions)
    {
        controller.openHandoffInstructions(error);
    }
    else if (b == &importResults)
    {
        mixFiles.clear();
        stemFiles.clear();
        tempoLockedStemFiles.clear();
        midiFiles.clear();

        if (shouldPromptForFamily(RequestedOutputFamily::Mix))
            chooseAndAddFiles(mixFiles, "Pick mix result file(s)");
        if (shouldPromptForFamily(RequestedOutputFamily::Stems))
            chooseAndAddFiles(stemFiles, "Pick stem result file(s)");
        if (shouldPromptForFamily(RequestedOutputFamily::TempoLockedStems))
            chooseAndAddFiles(tempoLockedStemFiles, "Pick tempo-locked stem file(s)");
        if (shouldPromptForFamily(RequestedOutputFamily::Midi))
            chooseAndAddFiles(midiFiles, "Pick MIDI file(s)");

        if (mixFiles.isEmpty() && stemFiles.isEmpty() && tempoLockedStemFiles.isEmpty() && midiFiles.isEmpty())
        {
            lastUiError = "Manual import cancelled: no files selected.";
            refreshOutputList();
            return;
        }

        ManualCompleteFiles completion;
        completion.mixFiles = mixFiles;
        completion.stemFiles = stemFiles;
        completion.tempoLockedStemFiles = tempoLockedStemFiles;
        completion.midiFiles = midiFiles;
        if (controller.manualCompleteActive(completion, error))
            lastUiError.clear();
    }
    else if (b == &importDropped)
    {
        if (importPendingDroppedFiles(error))
            lastUiError.clear();
    }
    else if (b == &clearDropped)
    {
        pendingDropFiles.clear();
        updateDropActions();
    }
    else if (b == &scanDownloads)
    {
        if (scanDownloadsForResultFiles(true, error))
            lastUiError.clear();
    }
    else if (b == &reveal)
    {
        revealSelectedOutput(error);
    }
    else if (b == &drag)
    {
        dragSelectedOutputToDaw(error);
    }

    if (error.isNotEmpty())
        lastUiError = error;
    else
        lastUiError.clear();

    refreshOutputList();
}

bool BridgeClientSurface::hasPendingManualImport() const
{
    const auto& job = controller.getActiveJob();
    if (job.id.isEmpty() || job.providerMode != ProviderMode::ManualSuno)
        return false;
    if (job.status != "awaiting_manual_provider_result"
        && job.status != "importing_provider_result"
        && job.status != "complete")
        return false;

    return shouldPromptForFamily(RequestedOutputFamily::Mix)
        || shouldPromptForFamily(RequestedOutputFamily::Stems)
        || shouldPromptForFamily(RequestedOutputFamily::TempoLockedStems)
        || shouldPromptForFamily(RequestedOutputFamily::Midi);
}

bool BridgeClientSurface::isSupportedDropFile(const juce::File& file) const
{
    return file.existsAsFile() && (isAudioExtension(file) || isMidiExtension(file));
}

RequestedOutputFamily BridgeClientSurface::guessedDropFamily(const juce::Array<juce::File>& files) const
{
    auto firstPending = [this](RequestedOutputFamily preferred)
    {
        if (shouldPromptForFamily(preferred))
            return preferred;
        if (shouldPromptForFamily(RequestedOutputFamily::Mix))
            return RequestedOutputFamily::Mix;
        if (shouldPromptForFamily(RequestedOutputFamily::Stems))
            return RequestedOutputFamily::Stems;
        if (shouldPromptForFamily(RequestedOutputFamily::TempoLockedStems))
            return RequestedOutputFamily::TempoLockedStems;
        if (shouldPromptForFamily(RequestedOutputFamily::Midi))
            return RequestedOutputFamily::Midi;
        return preferred;
    };

    if (files.isEmpty())
        return firstPending(RequestedOutputFamily::Mix);

    bool allMidi = true;
    bool anyTempoHint = false;
    bool anyStemHint = false;
    for (const auto& file : files)
    {
        allMidi = allMidi && isMidiExtension(file);
        const auto lowerName = file.getFileNameWithoutExtension().toLowerCase();
        anyTempoHint = anyTempoHint || hasTempoNameHint(lowerName);
        anyStemHint = anyStemHint || hasStemNameHint(lowerName);
    }

    if (allMidi)
        return firstPending(RequestedOutputFamily::Midi);
    if (anyTempoHint)
        return firstPending(RequestedOutputFamily::TempoLockedStems);
    if (anyStemHint || files.size() > 1)
        return firstPending(RequestedOutputFamily::Stems);
    return firstPending(RequestedOutputFamily::Mix);
}

void BridgeClientSurface::captureDroppedFiles(const juce::Array<juce::File>& files)
{
    pendingDropFiles.clear();
    for (const auto& file : files)
        if (isSupportedDropFile(file))
            pendingDropFiles.add(file);

    pendingDropFamily = guessedDropFamily(pendingDropFiles);
    dropFamily.setSelectedId(familyComboId(pendingDropFamily), juce::dontSendNotification);
    updateDropActions();
}

juce::String BridgeClientSurface::pendingDropSummary() const
{
    if (pendingDropFiles.isEmpty())
        return "Drop Suno result files here";

    const auto first = pendingDropFiles.getFirst().getFileName();
    juce::String summary = "Dropped " + juce::String(pendingDropFiles.size()) + " file";
    if (pendingDropFiles.size() != 1)
        summary << "s";
    summary << " -> " << familyLabel(pendingDropFamily) << " | " << first;
    if (pendingDropFiles.size() > 1)
        summary << " +" << juce::String(pendingDropFiles.size() - 1);
    return summary;
}

bool BridgeClientSurface::importPendingDroppedFiles(juce::String& errorOut)
{
    if (pendingDropFiles.isEmpty())
    {
        errorOut = "No dropped files waiting to import";
        return false;
    }
    if (! hasPendingManualImport())
    {
        errorOut = "No active manual_suno job is waiting for result files";
        return false;
    }
    if (! shouldPromptForFamily(pendingDropFamily))
    {
        errorOut = "Selected result family is not pending for this job";
        return false;
    }

    ManualCompleteFiles completion;
    switch (pendingDropFamily)
    {
        case RequestedOutputFamily::Mix:
            completion.mixFiles = pendingDropFiles;
            break;
        case RequestedOutputFamily::Stems:
            completion.stemFiles = pendingDropFiles;
            break;
        case RequestedOutputFamily::TempoLockedStems:
            completion.tempoLockedStemFiles = pendingDropFiles;
            break;
        case RequestedOutputFamily::Midi:
            completion.midiFiles = pendingDropFiles;
            break;
    }

    if (! controller.manualCompleteActive(completion, errorOut))
        return false;

    pendingDropFiles.clear();
    updateDropActions();
    return true;
}

bool BridgeClientSurface::isInterestedInFileDrag(const juce::StringArray& files)
{
    for (int i = 0; i < files.size(); ++i)
        if (isSupportedDropFile(juce::File(files[i])))
            return true;

    return false;
}

void BridgeClientSurface::fileDragEnter(const juce::StringArray&, int, int)
{
    externalFileDragActive = true;
    lastUiError.clear();
    refreshStatus();
}

void BridgeClientSurface::fileDragExit(const juce::StringArray&)
{
    externalFileDragActive = false;
    refreshStatus();
}

void BridgeClientSurface::filesDropped(const juce::StringArray& files, int, int)
{
    externalFileDragActive = false;
    updateControllerSettings();

    juce::Array<juce::File> droppedFiles;
    for (int i = 0; i < files.size(); ++i)
    {
        juce::File file(files[i]);
        if (isSupportedDropFile(file))
            droppedFiles.add(file);
    }

    juce::String error;
    if (droppedFiles.isEmpty())
    {
        error = "Drop a local audio or MIDI file.";
    }
    else if (hasPendingManualImport())
    {
        captureDroppedFiles(droppedFiles);
    }
    else if (droppedFiles.size() == 1 && isAudioExtension(droppedFiles.getFirst()))
    {
        if (controller.importAndSubmitAudio(droppedFiles.getFirst(), prompt.getText(), error))
            lastUiError.clear();
    }
    else
    {
        error = "Drop one audio file for an audio prompt, or use an active manual_suno job for result files.";
    }

    if (error.isNotEmpty())
        lastUiError = error;

    refreshOutputList();
}

juce::File BridgeClientSurface::downloadsFolder() const
{
    return juce::File::getSpecialLocation(juce::File::userHomeDirectory).getChildFile("Downloads");
}

juce::Array<juce::File> BridgeClientSurface::collectDownloadCandidates(bool includeSeen)
{
    juce::Array<juce::File> candidates;
    const auto folder = downloadsFolder();
    if (! folder.isDirectory())
        return candidates;

    auto files = folder.findChildFiles(juce::File::findFiles, false, "*");
    for (const auto& file : files)
    {
        if (! isSupportedDropFile(file))
            continue;

        const auto path = file.getFullPathName();
        if (includeSeen || ! seenDownloadPaths.contains(path))
            candidates.add(file);
        seenDownloadPaths.addIfNotAlreadyThere(path);
    }

    return candidates;
}

void BridgeClientSurface::seedSeenDownloadFiles()
{
    collectDownloadCandidates(true);
}

bool BridgeClientSurface::scanDownloadsForResultFiles(bool includeSeen, juce::String& errorOut)
{
    if (! hasPendingManualImport())
    {
        errorOut = "No active manual_suno job is waiting for result files";
        return false;
    }
    if (! downloadsFolder().isDirectory())
    {
        errorOut = "Downloads folder is not available";
        return false;
    }

    auto candidates = collectDownloadCandidates(includeSeen);
    if (candidates.isEmpty())
    {
        errorOut = includeSeen ? "No audio or MIDI files found in Downloads" : "";
        updateDownloadWatchStatus();
        return false;
    }

    captureDroppedFiles(candidates);
    updateDownloadWatchStatus();
    return true;
}

void BridgeClientSurface::updateDownloadWatchStatus()
{
    juce::String text = "Downloads: ";
    if (! downloadsFolder().isDirectory())
        text << "not found";
    else
        text << downloadsFolder().getFullPathName();
    if (watchDownloads.getToggleState())
        text << " | watching";
    downloadWatchLabel.setText(text, juce::dontSendNotification);
}

bool BridgeClientSurface::revealSelectedOutput(juce::String& errorOut)
{
    syncSelectedOutput();
    if (! selected.existsAsFile())
    {
        errorOut = "No completed output file selected";
        return false;
    }

    selected.revealToUser();
    return true;
}

bool BridgeClientSurface::dragSelectedOutputToDaw(juce::String& errorOut)
{
    syncSelectedOutput();
    if (! selected.existsAsFile())
    {
        errorOut = "No completed output file selected";
        return false;
    }

    performExternalDragDropOfFiles({ selected.getFullPathName() }, false);
    juce::SystemClipboard::copyTextToClipboard(selected.getFullPathName());
    return true;
}

void BridgeClientSurface::timerCallback()
{
    juce::String error;
    if (! controller.pollActive(error) && error.isNotEmpty())
        lastUiError = "Poll error: " + error;

    if (watchDownloads.getToggleState())
    {
        ++downloadWatchTick;
        if (downloadWatchTick >= 16)
        {
            downloadWatchTick = 0;
            juce::String watchError;
            if (pendingDropFiles.isEmpty() && hasPendingManualImport())
                scanDownloadsForResultFiles(false, watchError);
        }
    }

    refreshOutputList();
}

bool BridgeClientSurface::hasImportedFamily(RequestedOutputFamily family) const
{
    auto imported = controller.getState().lastImportedFamilies;
    if (! imported.isObject())
        imported = controller.getActiveJob().outputManifest.getProperty("importedDeliverables", juce::var());

    if (! imported.isObject())
        return false;

    auto files = imported.getProperty(importedDeliverablesKey(family), juce::var());
    return files.isArray() && files.getArray()->size() > 0;
}

bool BridgeClientSurface::isFamilyRequested(RequestedOutputFamily family) const
{
    auto requested = controller.getActiveJob().outputManifest.getProperty("requestedDeliverables", juce::var());
    if (requested.isObject())
    {
        const auto snakeCase = static_cast<bool>(requested.getProperty(requestedDeliverablesKey(family), juce::var(false)));
        const auto camelCase = static_cast<bool>(requested.getProperty(requestedDeliverablesCamelKey(family), juce::var(false)));
        return snakeCase || camelCase;
    }

    return controller.getState().requestedOutputs.contains(family);
}

bool BridgeClientSurface::shouldPromptForFamily(RequestedOutputFamily family) const
{
    return isFamilyRequested(family) && ! hasImportedFamily(family);
}

juce::String BridgeClientSurface::manualImportSummary() const
{
    juce::StringArray imported;
    if (hasImportedFamily(RequestedOutputFamily::Mix)) imported.add("mix");
    if (hasImportedFamily(RequestedOutputFamily::Stems)) imported.add("stems");
    if (hasImportedFamily(RequestedOutputFamily::TempoLockedStems)) imported.add("tempo_locked_stems");
    if (hasImportedFamily(RequestedOutputFamily::Midi)) imported.add("midi");

    if (imported.isEmpty())
        return "imported: none";
    return "imported: " + imported.joinIntoString(", ");
}

void BridgeClientSurface::resized()
{
    auto area = getLocalBounds().reduced(8);
    statusLabel.setBounds(area.removeFromTop(22));
    manualLabel.setBounds(area.removeFromTop(20));

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

    auto dropRow = area.removeFromTop(28);
    dropLabel.setBounds(dropRow.removeFromLeft(300));
    dropFamily.setBounds(dropRow.removeFromLeft(160));
    importDropped.setBounds(dropRow.removeFromLeft(140));
    clearDropped.setBounds(dropRow.removeFromLeft(130));

    auto downloadRow = area.removeFromTop(28);
    downloadWatchLabel.setBounds(downloadRow.removeFromLeft(360));
    scanDownloads.setBounds(downloadRow.removeFromLeft(150));
    watchDownloads.setBounds(downloadRow.removeFromLeft(170));

    auto row3 = area.removeFromTop(28);
    preview.setBounds(row3.removeFromLeft(130));
    reveal.setBounds(row3.removeFromLeft(120));
    drag.setBounds(row3.removeFromLeft(190));

    outputLabel.setBounds(area.removeFromTop(22));
    outputs.setBounds(area);
}
} // namespace suno::bridge
