#include "PluginProcessor.h"

class SunoStudioBridgeEditor;

SunoStudioBridgeProcessor::SunoStudioBridgeProcessor() = default;

const juce::String SunoStudioBridgeProcessor::getName() const { return "SunoStudioBridge"; }
void SunoStudioBridgeProcessor::prepareToPlay(double, int) {}
void SunoStudioBridgeProcessor::releaseResources() {}
bool SunoStudioBridgeProcessor::isBusesLayoutSupported(const BusesLayout&) const { return true; }
void SunoStudioBridgeProcessor::processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) {}

juce::AudioProcessorEditor* SunoStudioBridgeProcessor::createEditor()
{
    extern juce::AudioProcessorEditor* createSunoStudioBridgeEditor(SunoStudioBridgeProcessor&);
    return createSunoStudioBridgeEditor(*this);
}

bool SunoStudioBridgeProcessor::hasEditor() const { return true; }
double SunoStudioBridgeProcessor::getTailLengthSeconds() const { return 0.0; }
int SunoStudioBridgeProcessor::getNumPrograms() { return 1; }
int SunoStudioBridgeProcessor::getCurrentProgram() { return 0; }
void SunoStudioBridgeProcessor::setCurrentProgram(int) {}
const juce::String SunoStudioBridgeProcessor::getProgramName(int) { return {}; }
void SunoStudioBridgeProcessor::changeProgramName(int, const juce::String&) {}
void SunoStudioBridgeProcessor::getStateInformation(juce::MemoryBlock&) {}
void SunoStudioBridgeProcessor::setStateInformation(const void*, int) {}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new SunoStudioBridgeProcessor();
}
