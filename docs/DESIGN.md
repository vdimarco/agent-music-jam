# Interface design

The live-room design uses warm ivory type, moss-black surfaces, electric-lime transport and restrained musician accents. Georgia display type, a system sans-serif for controls, and monospace session labels create a studio identity without downloaded fonts or runtime assets.

Background `#121511`, panel `#1a1e18`, ink `#f1efdf`, muted `#adb2a2`, border `#363d30`, lime `#d3f87b`. Drums `#ee9d64`, bass `#8ed2b6`, keys `#b5a1e5`, lead `#e3ca79`.

Three areas separate the band, the direction and the human instrument. Keys instrument and tone controls are visible without opening advanced composition controls. The four-beat indicator follows scheduled audio time; note cells show actual scheduled events. Stop clears the beat display and buffered-time label. Reduced-motion preferences disable CSS transitions.

On narrow screens tracks stack, the keyboard precedes the conductor, and controls wrap without horizontal overflow. The native HTML controls retain visible keyboard focus and accessible names. The studio screenshot is the actual running interface. The release video documents the same audio workflow with the earlier visual theme.

## Performance workflow

Performance mode brings the audio transport, a four-bar chord strip, the recording timer and the human keyboard together. It uses the existing elements and handlers so switching views does not duplicate or interrupt playback. Band controls expand on demand. Chords follow the audio clock; arrangement labels use confirmed backend activation bars, with unallocated changes clearly identified as waiting.

The take shelf stores paired WAV/MIDI files in browser IndexedDB. The save dialog prevents accidental replacement and offers cancellation. Capacity failures preserve the current take. The interface states its exact-origin storage scope and recommends portable downloads.

## Further improvement

Named ensemble and instrument presets, followed by selectable keys and progressions, remain future work.
