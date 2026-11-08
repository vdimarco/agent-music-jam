# Verification report — 2026-11-08

Tests were run on this Linux machine with Python 3.14, Chromium, and the installed **Hermes Agent v0.23.0+684.gaf5c201**. These results distinguish live integrations from deterministic tests and simulated input.

## Results

| Area | Evidence | Result / limit |
| --- | --- | --- |
| Real Hermes catalog validator | `hermes plugins validate … --install-deps` | Pass: manifest, compatibility syntax, config schema, real registration probe, declared tools, security scan, no core overrides; no dependencies |
| Real Hermes loader/doctor | `hermes plugins doctor … --ci` | Pass, ten tools, zero hooks; registration does not launch service/audio |
| Real native tool handlers | Real `PluginContext`, `PluginManager` and scoped registry; invoke start, inspect, configure, stop | All four pass; launch token omitted from evidence |
| Real host-model conductor | `ctx.llm.complete_structured`, configured host provider, no injected mock | Pass in 3.17 s; correctly affected drums only |
| Real host-model musician | Separate drums role planner with shared ensemble state | Pass, 32 validated events |
| Active-turn native children | Implemented using `ctx.subagent_lifecycle` | Not end-to-end tested from a live parent Hermes conversation |
| Backend regression suite | `python -m unittest discover -s tests -v` | 14 tests pass |
| Slow composition | A test deliberately gates the planner while four bars are requested | Old pattern continues; returned change activates at bar 5, not a past deadline. This is a simulated slow model |
| Cancellation / selective undo | Stop during planning, undo one role, repeated undo | Pass; stale result discarded; unaffected roles preserved; repeated undo walks backward |
| Arrangement | Four-bar solo and automatic lead return | Pass in deterministic suite; exercised in recorded browser demo |
| Actual Web Audio playback | Browser AudioContext, scheduled oscillators, AudioWorklet PCM capture | Nonzero real output, not a mock sound engine |
| Scheduling | 22-second browser regression take | 249 events scheduled; zero late events; minimum observed scheduling lead approximately 289 ms; roughly 6.8 s buffered during the measured sample |
| Demo scheduling | Approximately 47 s of live audio in a 49.43 s video | 412 events scheduled; zero late events; minimum observed lead approximately 279 ms; about 5.8 s remaining at final sample |
| Stop | Real Web Audio voice-set inspection after Stop | Zero remaining voices |
| Mixer | Real browser mute/solo controls, live role gains, exports | Controls exercised; WAV includes actual mixer output; MIDI captures onset dynamics and mute truncation |
| On-screen input | Real browser pointer down/up on piano keys | Phrase capture, notes in human MIDI track and recorded WAV; demo keyboard played through automation |
| MIDI controller handling | Explicitly selected simulated Web MIDI device | Note-on/off, sustain release and all-notes-off pass; no claim of physical hardware verification |
| Instruments/tone | OfflineAudioContext renders using the same synthesis code | All ten instrument pairs differ (RMS difference ≥0.0289); dark/bright piano RMS difference 0.0857 |
| Save / restore | Real browser downloads JSON, file upload restore, selections inspected | Pluck instrument, bright tone, band organ and mixer/session state survive; restored stopped |
| MIDI validity | Independent binary parser checks all tracks, meta lengths, events and note pairs | Type 1, 480 PPQ, six tracks; 167 drum, 54 bass, 128 keys, 14 lead and 7 human note-ons in the demo; zero dangling note pairs |
| WAV validity | PCM decoded with Python `wave` | Test take: mono 48 kHz / 16-bit, 22.293 s, peak 0.2334 FS, RMS 0.02488 FS; no clipping |
| Demo media | `ffprobe` on supplied MP4 | H.264 video + AAC audio; 49.43 seconds; music comes from that actual browser take |
| Browser health | Desktop and 390 px mobile inspection | No JavaScript errors in regression; no horizontal overflow at 390 px |
| Local security | Real HTTP requests with missing/wrong token, foreign Origin, path traversal | Rejected; authenticated same-origin request succeeds; exports contain no local token |

The runtime test scripts and detailed numerical evidence are included under `tests/` and `docs/evidence/`. Screenshots and media sit beside the source package rather than inside the source-only archive.

## Reproduce

Core checks need no extra dependencies:

```sh
python -m unittest discover -s tests -v
hermes plugins doctor . --ci
hermes plugins validate . --install-deps
```

The optional real-browser test requires Chromium and Playwright. Install the test dependency into a scratch directory, not the plugin runtime:

```sh
npm install --prefix work/browser playwright@1.58.2 --no-audit --no-fund
NODE_PATH="$PWD/work/browser/node_modules" node tests/browser.cjs
```

Set `CHROMIUM` if the executable is not `/usr/bin/chromium`, and `PYTHON` if the interpreter is not named `python`. This test starts a separate loopback service and shuts it down; it does not control an existing user jam. It writes screenshots, a small take, session JSON and diagnostics into ignored `work/browser-check/`.

## Remaining verification and publication gates

- Physical MIDI controllers, audio-interface latency, Bluetooth output and acoustic speaker quality were not verified.
- Safari/Firefox, browser suspension/OS sleep recovery and long-duration soak behavior were not certified.
- Native child sessions are implemented but still need a parent-turn end-to-end run; live `ctx.llm` role planning was verified separately.
- The demo uses **local rule planners**, clearly identified in the UI. It is not presented as a model/subagent demo. Its piano phrase is automated UI input, not a claimed human hardware performance.
- The catalog needs a real public repository and pinned commit before submission. No catalog PR or publication was performed.

## Studio redesign verification

The final studio interface was checked in Chromium at 1440 × 1280 and 390 × 844. Playback, visible band sound controls, instrument/tone persistence, phrase input, mute/solo, undo, WAV/MIDI downloads and restore passed. The beat indicator follows playback and clears on Stop. No page errors, mobile overflow or late events occurred (249 events). See `docs/evidence/browser.json` and `docs/screenshots/studio.png`. The performance demo predates the visual redesign.

## v0.1.1 performance and take workflow

`tests/performance.cjs` passed against a separate real Chromium instance at 1440 × 900 and 390 × 844. The keyboard fits the first viewport in performance mode at both sizes. Tested audio-clock chord highlighting, confirmed arrangement bars, recording duration, canceling replacement without losing samples, saving and continuing, explicit discard, real IndexedDB capacity failures preserving audio, paired WAV/MIDI downloads with valid headers, persistence through reload, and MIDI export leaving WAV protection active. No page errors or mobile horizontal overflow. `tests/browser.cjs` also passed playback, instrument/tone, mixer, undo, export and restore regression coverage (249 scheduled events, zero late events).

Saved takes are explicitly scoped to the browser origin (including the service port), capped at ten takes / 100 MB, and never silently evicted by app code. Browser eviction, forced shutdown and platform-specific leave-page warning behavior are not verified. Downloads are recommended for permanent backups.
