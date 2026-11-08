# Architecture and scope

`__init__.py` registers the native tools, with a lazy locked service and unload cleanup. `server.py` serves local static assets and authenticated JSON endpoints. `engine.py` owns the shared conductor state under a reentrant lock. `planning.py` interprets directions and generates bounded role-specific patterns. `music.py` validates data and serializes standard MIDI. `web/audio.js` owns all synthesis and scheduling; `web/recorder.js` captures the mixed output off the main thread. `web/app.js` connects controls and input to those surfaces.

## Data and concurrency

Events carry a zero-based bar (0–3 in a four-bar pattern), beat, MIDI pitch, beat duration, normalized velocity, role/instrument and supported articulation. Monophonic bass/lead, six-voice keys and five-voice drums are validated by a sweep of note endpoints. Events cannot extend beyond their bar. Harmonic context is shared, while each role retains its pattern, motif, controls, intention and selective undo stack.

Only one conductor job runs at a time. It snapshots the ensemble, plans outside the session lock, then atomically queues the completed batch. Stop/restore increments a generation; configure/undo increments the affected role’s revision. Old results cannot commit after either kind of invalidation. The four role planners are explicit stateful planners; no claim is made that they run independent continuous conversations.

The browser requests contiguous bars and receives an immutable snapshot for each. A request applies all ready role changes before constructing that bar. Delayed changes use the next unscheduled bar as their origin, not an already elapsed wall-clock promise. A drummer fill is aligned to the fourth bar of the harmonic turnaround. Undo skips writing another undo history entry, so repeated undo walks backward rather than toggling.

Web Audio schedules every note and its release ahead of time. Mute/solo acts through role gains without rewriting other musicians. A browser-side interval, independent of visual animation frames, refills the buffer. Visual highlighting uses actual event timestamps. An AudioWorklet records the real master output into bounded chunks; no model call or file download runs in its process callback.

## Deliberate first-version limits

- One supported harmonic ensemble, fixed key/meter; tempo changes require a fresh stopped jam.
- No microphone transcription, voice commands, sample loading, network collaboration, automatic publishing or provider-specific credentials.
- Local-rule mode supports a small documented direction vocabulary; arbitrary semantics require Hermes model access.
- Instrument selection affects future synthesis nodes. Tone and mixer gain can change current nodes. MIDI approximates instruments and note-on dynamics; WAV preserves the actual performance.
- Browser suspension, OS sleep and severe rendering stalls can exhaust finite audio buffering. Keep the jam tab active for a performance; counters reveal missed scheduling deadlines.
- Unloading the plugin closes the service. A browser with already scheduled notes releases on its local Stop; if the host disappears abruptly, its finite scheduled notes end normally.
- Real Hermes LLM calls and loader validation were exercised. Native child-session orchestration needs an active Hermes turn and is not claimed as end-to-end verified in this delivery.
