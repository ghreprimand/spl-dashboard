# Developer reference — 0.5.0

Read [AGENTS.md](../AGENTS.md), [README](../README.md) and all current documents
before changing architecture, DSP, calibration or terminology. Current source is
executable truth; older ADRs record the decisions at their original release.
See [handoff](HANDOFF.md) for evidence and verification status.

## Repository map

| File | Responsibility |
| --- | --- |
| `server/src/spl_dashboard/main.py` | FastAPI lifecycle, one-process lock, middleware, routes, CSV streaming and static UI |
| `models.py` | Strict Pydantic configuration/telemetry models; unknown fields and nonfinite numbers rejected |
| `runtime.py` | Capture orchestration, configuration lock, health, shared frame, events, mapping captures |
| `capture.py` | Demo, PCM WAV, PortAudio input, USB/ALSA identity and gain inspection |
| `calibration.py` | Vendor file parsing, FIR construction and supported UMIK sensitivity conversion |
| `dsp.py` | Weighting filters, causal calibration processing, Slow, rolling energy and held peaks |
| `spectrum.py` | Separate raw-PCM multiresolution FFT analysis and power-conserving band projection |
| `storage.py` | SQLite configuration, events/frames/annotations and mapping library |
| `web/src/App.tsx` | Dashboard/strip, settings, event controls and saved mapping management |
| `AudienceMapping.tsx` | Guided five-position workflow and equal-energy difference calculation |
| `SpectrumAnalyzer.tsx` | Canvas plot, detail controls, cursor/freeze/local band maxima |
| `useTelemetry.ts` | WebSocket freshness/reconnection and wake handling |
| `api.ts`, `types.ts` | HTTP client, telemetry shape checks and TypeScript contracts |
| `layout.ts`, `spectrumOptions.ts` | Validated browser-local preferences |
| `styles.css` | Strip/container responsiveness and dashboard styling |
| `deploy/` | systemd service and Avahi service advertisement |
| `scripts/` | Single-process launcher and synthetic WAV generator |
| `server/tests/`, `web/src/*.test.*` | Deterministic calculations, API/persistence, input and UI tests |

Python imports are rooted at `server/src`. Tests add that path via pyproject.
Installed wheels run their installed package, not an arbitrary copied source tree.
Frontend production files are built into ignored `web/dist`; runtime has no Node
requirement. Dependencies are declared in `server/pyproject.toml` and
`web/package.json`; npm versions are locked in `web/package-lock.json`. Python
ranges are not a fully pinned deployment lockfile.

## Configuration contract

`GET /api/config` returns settings. `PUT /api/config` is a full replacement, not
PATCH: omitted fields take model defaults. Read/modify/write the current object.
Configuration writes restart capture and are refused during recording. The input
channel is zero-based in the API and one-based in the UI.

| Fields | Default / interpretation |
| --- | --- |
| `mode`, `device`, `channel`, `sampleRate` | `demo`, empty, 0, 48000; device mode requires explicit ID |
| `wavPath` | Empty; WAV mode requires an existing file within data-dir `fixtures/` |
| `calibrationText`, `confirmedMicSerial` | Original vendor contents and operator's physical serial confirmation |
| `calibrationMode` | `auto`; alternatives `reference`, `off` |
| `referenceDb`, `referenceRmsDbfs`, `referenceNote` | Null/null/empty; both numeric values and an explanatory note required for a reference |
| `fieldTrimDb` | 0; additional calibration trim, ±20 dB; not venue compensation |
| `lasThreshold`, `leqThreshold`, `peakThreshold` | Null disables; checks measured LAS, LAeq10, LCpeak respectively |
| `venueName`, `audienceOffsetDb`, `audienceMappingNote` | Empty/null/empty; named A-only offset ±30 dB and retained capture JSON |
| `audienceDisplay` | Nullable migration default: existing mapping selects estimates, no mapping selects measured; explicit bool persists |

See `models.py` for exact range/length limits. Automatic mode with a supplied
reference pair is normalized to reference mode. Calibration state describes
applied conversion, not independent physical certification.

## State ownership and lifecycle

- Host: input/configuration, calculations, alarm thresholds, events, map library,
  loaded map and measured/estimated display selection.
- Browser: `spl-layout-v1` size/position/details; `spl-spectrum-v2` analyzer detail,
  averaging/style/top/range. Obsolete local `audience` is ignored. Freeze/cursor
  and local spectrum maxima are not measurement holds or shared event state.
- `PUT /api/reading-location` takes `{"audience": true|false}`. It does not reset
  input/averages and is allowed during recording. True requires a loaded offset.
- New mapping apply uses full configuration; saved activate and clear use current
  settings under the lock. All three restart input/averages and require no event.
- Clear unloads only mapping fields and selects measured mode; the library entry
  survives. Delete removes an unloaded library entry after UI confirmation, not
  old event snapshots. A loaded map cannot be deleted even when its display is off.
- Event start rebuilds calculations/reset holds. Event stop preserves the log;
  there is no pause/resume operation for a stopped event.
- Input gaps reset filters/averages, preserve holds, and record gap state. An
  active-event service restart restores holds from its last durable frame and
  records an interruption. Without an active event, old holds are not restored.
- Warm-up is elapsed valid sample coverage; an incomplete rolling average is
  displayed with a warning rather than pretending a full 60/600 seconds exists.

Mapping metadata dates come from the applying browser's clock. Five measurements
carry durations, level, device and calibration identity but no individual UTC
capture times. The frontend computes the guided correction and consistency checks;
the API accepts validated settings and does not prove the provenance of those
captures. Reusing a saved map copies its mapping fields, not old input settings;
the operator must verify unchanged room, speaker arrangement and mic position.

## Timing, warnings and concurrency

48 kHz / 4800-sample blocks produce 100 ms calculations. Spectrum `HOP=2400` is an
internal buffer subdivision, not production 20 Hz delivery. See
[spectrum analyzer](spectrum-analyzer.md) for windows and normalization. Heartbeat
and WebSocket cadence are distinct from sample-time integration. Render animation
may be faster than the 10 Hz telemetry without improving measurement resolution.

Raw amplitude near digital full scale triggers clipping; it is not inferred from
SPL. The indication is held briefly. Invalid/disconnected input must remain visible.
The browser marks a silent link stale after about two seconds, closes it after
five seconds and retries after 1.5 seconds. Wake/visibility changes reconnect.
Runtime also checks age independently. `validationPending` and the internal
`umik-unverified` source intentionally remain despite FILE CAL.

A configuration lock serializes configuration, profile activation/clear, display
choice and event start; mapping capture separately detects processor changes.
Device access has capture-layer synchronization. The main SQLite writer stays on
the event-loop thread; chart history opens a separate read-only connection in a
worker. One Uvicorn worker and one process per data directory are mandatory.

## Persistence and protocol details

[Architecture](architecture.md) lists every application route. FastAPI also exposes
`/docs`, `/redoc` and `/openapi.json`. Mutation requests need
`X-SPL-Client: dashboard`. This is browser cross-origin protection, not credentials.
A supplied Origin is compared to Host; a missing Origin is allowed. The declared
Content-Length check is not a universal streaming upload limit.

SQLite uses WAL and FULL synchronous. Tables are `config`, `events`, `frames`,
`annotations`, `audience_mappings`; one partial unique index enforces a single
active event. Configuration and map snapshots are JSON. Mapping IDs are the first
24 SHA-256 hex characters over name/offset/capture-note JSON, so identical resaves
deduplicate while new dated captures remain separate. Startup migrates the current
map only; previously overwritten maps are not reconstructed from history.

Events list returns the newest 200 events. Chart history returns the latest 600
records chronologically with timestamp/eventId/measured/status only. Missing
history yields an empty list. Summary/CSV for an unknown event return 404;
invalid operations generally return 400 and model validation returns 422.

Full telemetry (including spectrum and reading location) is stored in frames.
CSV exports selected scalar fields; JSON summary exports metadata only. Neither
is a full database/library backup. There is no retention deletion, bulk mapping
export/import, database schema-version framework or authentication layer.

## Development and troubleshooting

Use `make server-install`, `make web-install`, then `make dev-server` and
`make dev-web`. Ports are 8000 and 5173. `SPL_API_TARGET` can point Vite at another
backend; it proxies `/api` and `/ws` while retaining Origin/Host behavior.
`SPL_DATA_DIR` isolates a developer database; do not run test changes on an event
appliance's live data. `SPL_WEB_DIST` chooses built assets; static routes are
registered only when that directory exists at application creation.

Run `make check` before commits (Ruff, Python/web tests, mypy, TypeScript, build).
Browser unit tests use JSDOM; Canvas warnings there do not establish actual render
correctness. Verify important display changes with a real browser, and iPad window
behavior on the physical tablet. Numerical tests cannot replace microphone or
long-run appliance acceptance. Current 0.5.0 checks: 123 Python + 23 web tests.

| Symptom | First check |
| --- | --- |
| Mapping capture disabled | Stop active recording; UI displays the reason |
| Can't delete loaded map | Clear loaded mapping, then select its library entry and delete |
| Tablet differs after upgrade | Reload to load new JS, then verify shared mapping identity |
| No SPL numbers | Input connected, FILE/REFERENCE CAL applied, explicit device and matching file/serial |
| File correct but gain changed | Check actual USB gain descriptor and diagnostics; do not edit vendor Sens Factor blindly |
| Stale display | LAN/WS connection, microphone/input age, service state; no cloud connection needed |
| Peak unexpectedly high | Distinguish held C peak from A-weighted Slow/average; use separate peak reset |
| Backend edit has no effect | Check installed wheel vs editable venv and restart service |
| Input failure after reboot | Selected stable USB identity/port, audio permissions, `journalctl -u spl-dashboard -n 100` |
| History/logging problem | Disk space, SQLite/write error, event ID and health fields |

Do not expose calibration files, private SSH keys, database backups or event data
in source control. `.gitignore` excludes local `UMIKCal/`, SQLite and build output.
Deployment, backups and rollback are covered in [deployment](deployment.md).
