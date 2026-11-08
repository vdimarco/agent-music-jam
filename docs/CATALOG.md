# Catalog submission preparation

Checked against the official [plugin guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins), [LLM access](https://hermes-agent.nousresearch.com/docs/developer-guide/plugin-llm-access), [subagent lifecycle API](https://hermes-agent.nousresearch.com/docs/developer-guide/subagent-lifecycle-api), and [catalog submission rules](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission) on 2026-11-08.

Public source: https://github.com/vdimarco/agent-music-jam. Release assets: https://github.com/vdimarco/agent-music-jam/releases/tag/v0.1.1. Catalog admission remains subject to CI and human maintainer review. The submitted catalog entry pins the exact validated source commit.

## Proposed listing copy

**Agent Music Jam — a band you can jam with**

Conduct four AI musician roles while a local synthesized groove keeps playing. Play an on-screen keyboard or selected MIDI controller, change one part on a future bar, undo that musician, and export multitrack MIDI or the actual WAV performance.

Native tools, host-owned LLM access, supported child-session lifecycle for active-turn requests, profile-scoped state, and a separate loopback browser audio engine. No core overrides, self-updater, telemetry or bundled executable payloads.

## PR description draft

Agent Music Jam adds a local live-band workflow with drums, bass, keys and lead. A conductor and role-scoped planners compose ahead while Web Audio schedules validated notes against the audio clock. Changes activate on available bar boundaries; late/failed planning preserves the existing pattern. The browser includes mixer, keyboard, explicitly selected MIDI input, instrument/tone controls, selective undo, JSON save/restore, multitrack MIDI and recorded PCM WAV.

Surfaces: ten `ctx.register_tool` tools, `ctx.on_unload`, `ctx.get_config`, `ctx.state`, `ctx.llm.complete_structured`, and `ctx.subagent_lifecycle` for supported active-turn calls. No privileged override capabilities requested.

Disclosures: `jam_start` creates an authenticated loopback HTTP server and daemon threads that live until plugin unload. Model requests send musical context, user directions and human note phrases through Hermes’s configured provider. The plugin reads its own web assets and user-selected session JSON; saves its own plugin state; downloads exports in the browser. User-kept WAV/MIDI takes are stored in browser IndexedDB at the local origin, bounded to ten takes / 100 MB. It invokes no shell, reads no credential files, stores no model credentials, and uses no telemetry or remote assets. MIDI device access requires explicit browser permission and device selection. The local launch token is held in browser session storage for that tab.

Validation evidence: include `docs/VERIFICATION.md`, the current studio screenshot, and the approximately 50-second actual-music demo (recorded with the earlier UI theme). Disclose that the demo uses local rule planners and automated piano input; the real host model was tested separately. Physical MIDI hardware and active-turn native child execution remain unverified.

## Publication checklist

1. Choose and create the public source repository under the owner’s account.
2. Commit only reviewable source, license, docs and tests; keep demo media outside the source-only release tree.
3. Run `hermes plugins validate . --install-deps` against the exact proposed commit; retain the full SHA.
4. Prepare `plugin-catalog/agent-music-jam.yaml` using the current catalog entry schema, with the real public `repo`, 40-character `sha`, quoted version `"0.1.1"`, and `requires_hermes: ">=0.23.0"`. Do not submit placeholder URLs or SHAs.
5. Add screenshot/demo links and the disclosure text above. Submit as repository owner or major contributor; await catalog CI and human review.

Updates must be new SHA-bump PRs. This plugin contains no self-updater.
