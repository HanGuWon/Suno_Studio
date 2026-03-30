# Host Capability Matrix

This matrix captures transport/edit interoperability across common host integrations and media formats.

| Host | Version | Format | Transport fields available | Edit cursor access | Selection export | Auto media insertion | ARA availability | Drag-and-drop reliability notes |
|---|---|---|---|---|---|---|---|---|
| Pro Tools | 2024.10+ | WAV | Tempo, time signature, bars|beats, sample rate | ❌ | ❌ | ❌ | ❌ | Reliable clip drag to timeline; drag to marker lanes can fail when Edit and Mix windows are split. |
| Logic Pro | 11.x | WAV/AIFF | Tempo map, cycle range, SMPTE start | ✅ | ✅ | ✅ | ❌ | Very reliable in Tracks area; occasional drop miss on frozen tracks. |
| Cubase Pro | 13.x | WAV | Tempo track, ruler format, frame rate | ✅ | ✅ | ✅ | ✅ | Reliable drag in Project window; disable “Constrain Delay Compensation” for consistent insertion timing. |
| Nuendo | 13.x | WAV/BWF | Tempo track, markers, frame rate | ✅ | ✅ | ✅ | ✅ | Reliable for audio tracks; drag to ADR panels is less consistent. |
| Studio One | 6.6+ | WAV | Tempo, arranger sections, song position | ✅ | ✅ | ✅ | ✅ | High reliability; occasional duplicate insert if drop occurs during playback. |
| Ableton Live | 12.x | WAV | Tempo, global quantization, song time | ❌ | ❌ | ❌ | ❌ | Drag to Session View clips is reliable; Arrangement drop may offset if warp is enabled. |
| Reaper | 7.x | WAV/FLAC | Tempo map, project sample rate, play state | ✅ | ✅ | ❌ | ❌ | Reliable drag to arrange view; drag to razor-edited lane can target wrong take if lane is collapsed. |
| FL Studio | 21.x | WAV/MP3 | Tempo, song/pattern mode, PPQ | ❌ | ❌ | ❌ | ❌ | Drag works into Playlist and Sampler; edge drops near playlist bounds can be ignored. |
