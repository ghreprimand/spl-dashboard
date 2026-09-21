# Architecture

## Data flow

```text
Selected input @ 48 kHz, 4800 samples / 100 ms
  +-> raw health / clipping diagnostics
  +-> 2049-tap calibration FIR -> 4x interpolation -> A/C weighting
  |      -> Slow, 60/600 s energy averages, held maximum and C peak
  +-> raw PCM -> multiresolution Hann FFT -> file correction per frequency
         -> fractional-octave band energy and optional power averaging

Runtime snapshot -> /ws/telemetry (10 Hz) -> browser strip / analyzer
                 -> active-event SQLite records (approximately 1 Hz)
                 -> selected-field CSV export
```

The server owns truth and state. Closing the browser must not pause averages,
peak hold, alarms, or logging.

## Implemented stack

- Linux host, Python 3.11+
- PortAudio via `sounddevice` for host capture
- NumPy/SciPy for explicitly tested DSP
- FastAPI/Uvicorn for HTTP and WebSocket service
- SQLite for event metadata and one-second telemetry records
- React + TypeScript + Vite for the LAN web client
- mDNS/Avahi hostname `splbox.local`
- systemd units for service startup and restart

The service owns measurement state. Browser animation does not create additional measurements.

## Network API

Current endpoints (see `main.py`):

- `GET /api/health` — status, mode, schema version, input flags.
- `GET /api/config`, `PUT /api/config` — read/replace settings (PUT rejects if an
  event is recording, restarts capture and averaging windows).
- `GET /api/telemetry` — latest snapshot; `WS /ws/telemetry` streams 10 Hz.
- `GET /api/devices` — input discovery; PortAudio cache refresh is permitted only while no stream is open.
- `PUT /api/reading-location` — display-only measured/estimated toggle; allowed
  during recording and does **not** restart capture.
- `POST /api/audience-mapping/capture` — one 30 s guided A-weighted capture.
- `POST /api/audience-mapping/clear` — unload the active mapping on all clients.
- `GET /api/audience-mappings`, `POST /api/audience-mappings/{id}/activate`,
  `DELETE /api/audience-mappings/{id}` — durable mapping library.
- `POST /api/events`, `POST /api/events/current/stop`,
  `GET /api/events/current`.
- `POST /api/events/current/annotations`,
  `POST /api/events/current/reset-peak`,
  `POST /api/events/current/reset-maximum`.
- `GET /api/events`, `GET /api/events/{id}/history` (chart-only),
  `GET /api/events/{id}/summary.json` (event metadata), and
  `GET /api/events/{id}/export.csv`.

Non-`GET`/`HEAD`/`OPTIONS` requests require an `X-SPL-Client: dashboard` header,
reject a supplied Origin whose network location differs from Host. The middleware
rejects a declared Content-Length above 300000 bytes; this is not a streaming body
size limit or authentication. Requests without Origin are allowed with the header. `models.py` defines
schema version 2.

`summary.json` returns event **metadata only** — the event row, its stored
configuration (including original calibration text and reference notes),
annotations and a frame count — not the per-frame telemetry. Full one-second
frames live in SQLite; `export.csv` exposes selected scalar fields, not spectra or
complete frame objects. The CSV carries raw
LAS/LAeq1/LAeq10/LCpeak/LASmax plus estimated LAS/LAeq1/LAeq10; there is no
estimated-LASmax column even though the frame object can hold one.

## Telemetry schema v2

- `source`: `demo`, `wav-unverified`, or `umik-unverified`.
- `status`: connected/reference-set/clipping/stale/validation flags, warm-up,
  gap/overrun counters and logging failure.
- `diagnostics`: raw RMS/peak dBFS, sample rate, calibration identity, sample
  count, input age, applied offset, calibration method/model and input gains.
- `measured`: nullable LAS, LAS maximum, LAeq1, LAeq10 and LCpeak acoustic fields. The entire
  object is null without supported file calibration or an acoustic reference
  (except labelled demo values).
- `estimatedAudience`: separate nullable A-only corrected values; no C-peak estimate.
- `spectrum`: unweighted FFT band energies with explicit dBFS/dB SPL units.
- `readingLocation`: shared audience/measured choice with the loaded mapping's
  id, name, offset and browser mapping-apply date; travels to every client so display mode is
  server-owned, not browser-local.
- `timestamp`, `sequence`, `eventId`, `peakHold`, `alarms`.

The source loop operates independently from clients. A separate heartbeat updates status and stores approximately one frame per second;
each WebSocket handler sends the current snapshot on 100 ms deadlines. Capture/DSP uses
sample counts for integration; monotonic time tracks input freshness and logging
cadence; UTC identifies records. SQLite event configuration includes original
calibration text and reference notes. A separate additive `audience_mappings`
table holds immutable, content-hashed mapping snapshots (name, correction and
full capture note); the active mapping is migrated into it idempotently at
startup. No raw audio is stored.

One process/worker owns the data directory and measurement state. See ADR 0002
for restart, calibration and per-browser layout decisions.

## Security and privacy

- Binds all interfaces by default; use a trusted LAN/firewall. No cloud telemetry.
- Never store or expose raw audio.
- Bind to the event network only where practical.
- Add optional dashboard authentication before use on untrusted shared LANs.
- Avoid putting secrets in browser storage or the repository.

## Reliability

- Continue measuring and logging with zero clients.
- Use monotonic time for integration windows and wall time for records.
- Detect dropped/overrun audio buffers.
- Persist event state frequently enough to recover after power loss.
- Mark gaps rather than interpolating missing measurements.
- Keep the last good frame visually stale rather than silently freezing it.


The dashboard history endpoint returns chart-only records (timestamp, eventId,
measured and status) using SQLite JSON extraction. It avoids repeatedly decoding
and serializing full spectra on the capture event loop during recording. Full
telemetry remains in storage; exports expose only the documented subset. Recovery
uses the full stored record.

History reads use a separate read-only SQLite connection in a worker thread,
keeping JSON extraction out of the capture event loop. Raw logs remain unchanged.
