# Interface design

The live-room design uses warm ivory type, moss-black surfaces, electric-lime transport and restrained musician accents. Georgia display type, a system sans-serif for controls, and monospace session labels create a studio identity without downloaded fonts or runtime assets.

Background `#121511`, panel `#1a1e18`, ink `#f1efdf`, muted `#adb2a2`, border `#363d30`, lime `#d3f87b`. Drums `#ee9d64`, bass `#8ed2b6`, keys `#b5a1e5`, lead `#e3ca79`.

Three areas separate the band, the direction and the human instrument. Keys instrument and tone controls are visible without opening advanced composition controls. The four-beat indicator follows scheduled audio time; note cells show actual scheduled events. Stop clears the beat display and buffered-time label. Reduced-motion preferences disable CSS transitions.

On narrow screens tracks stack, the keyboard precedes the conductor, and controls wrap without horizontal overflow. The native HTML controls retain visible keyboard focus and accessible names. The studio screenshot is the actual running interface. The release video documents the same audio workflow with the earlier visual theme.

## Suggested next improvements (not implemented)

1. Compact performance view: keep transport and keyboard within reach while playing, with expandable musician controls.
2. Take protection: recording duration, a visible take library and a warning before replacing an unexported recording.
3. Chord and arrangement timeline: show the current chord and confirmed future activation bars.
4. Musical presets: save named ensembles and sound/mix presets, followed by selectable keys and progressions.
