cmake_minimum_required(VERSION 3.22)
project(SunoStudioPluginClient VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(MSVC)
  add_compile_options(/utf-8)
endif()

option(SUNO_STUDIO_FETCH_JUCE "Fetch JUCE automatically when find_package cannot locate it" ON)
set(SUNO_STUDIO_JUCE_TAG "8.0.14" CACHE STRING "JUCE git tag used when SUNO_STUDIO_FETCH_JUCE is ON")

find_package(juce CONFIG QUIET)
if(NOT juce_FOUND AND SUNO_STUDIO_FETCH_JUCE)
  include(FetchContent)
  message(STATUS "JUCE package not found; fetching JUCE ${SUNO_STUDIO_JUCE_TAG}")
  FetchContent_Declare(
    juce
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG ${SUNO_STUDIO_JUCE_TAG}
    GIT_SHALLOW TRUE
  )
  set(JUCE_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
  set(JUCE_BUILD_EXTRAS OFF CACHE BOOL "" FORCE)
  FetchContent_MakeAvailable(juce)
elseif(NOT juce_FOUND)
  message(FATAL_ERROR "JUCE not found. Set juce_DIR or enable SUNO_STUDIO_FETCH_JUCE.")
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

target_compile_definitions(bridge_client
  PUBLIC
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_MODAL_LOOPS_PERMITTED=1
)

set(SUNO_STUDIO_PLUGIN_FORMATS VST3)
if(APPLE)
  list(APPEND SUNO_STUDIO_PLUGIN_FORMATS AU)
endif()

juce_add_plugin(SunoStudioBridgePlugin
  COMPANY_NAME "SunoStudio"
  IS_SYNTH FALSE
  NEEDS_MIDI_INPUT FALSE
  NEEDS_MIDI_OUTPUT FALSE
  IS_MIDI_EFFECT FALSE
  COPY_PLUGIN_AFTER_BUILD FALSE
  PLUGIN_MANUFACTURER_CODE SsBr
  PLUGIN_CODE SsBp
  FORMATS ${SUNO_STUDIO_PLUGIN_FORMATS}
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
