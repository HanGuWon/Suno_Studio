cmake_minimum_required(VERSION 3.22)
project(SunoStudioPluginClient VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(juce CONFIG QUIET)
if(NOT juce_FOUND)
  message(FATAL_ERROR "JUCE not found. See plugin_juce/README.md for setup instructions.")
endif()

add_library(bridge_client STATIC
  src/BridgeDiscovery.cpp
  src/BridgeModels.cpp
  src/BridgeHttpClient.cpp
  src/PluginStateStore.cpp
  src/BridgeController.cpp
  src/BridgeClientSurface.cpp
)

target_include_directories(bridge_client PUBLIC include)

target_link_libraries(bridge_client
  PUBLIC
    juce::juce_core
    juce::juce_events
    juce::juce_data_structures
    juce::juce_audio_formats
    juce::juce_cryptography
    juce::juce_gui_basics
    juce::juce_gui_extra
)

juce_add_plugin(SunoStudioBridgePlugin
  COMPANY_NAME "SunoStudio"
  IS_SYNTH FALSE
  NEEDS_MIDI_INPUT FALSE
  NEEDS_MIDI_OUTPUT FALSE
  IS_MIDI_EFFECT FALSE
  COPY_PLUGIN_AFTER_BUILD FALSE
  PLUGIN_MANUFACTURER_CODE SsBr
  PLUGIN_CODE SsBp
  FORMATS VST3 AU
  PRODUCT_NAME "Suno Studio Bridge"
)

target_sources(SunoStudioBridgePlugin PRIVATE
  src/PluginProcessor.cpp
  src/PluginEditor.cpp
)

target_link_libraries(SunoStudioBridgePlugin PRIVATE
  bridge_client
  juce::juce_audio_utils
)

juce_add_gui_app(SunoStudioBridgeStandalone
  PRODUCT_NAME "Suno Studio Bridge Standalone"
)

target_sources(SunoStudioBridgeStandalone PRIVATE
  standalone/StandaloneMain.cpp
)

target_link_libraries(SunoStudioBridgeStandalone PRIVATE
  bridge_client
)

juce_add_console_app(BridgeContractVectors PRODUCT_NAME "BridgeContractVectors")
target_sources(BridgeContractVectors PRIVATE tests/BridgeContractVectors.cpp)
target_link_libraries(BridgeContractVectors PRIVATE bridge_client)
