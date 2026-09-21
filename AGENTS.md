# Agent instructions

Read `README.md` and every document under `docs/` before changing architecture,
DSP, calibration, or terminology.

## Non-negotiable product rules

- The appliance must operate without internet access on an event LAN.
- The measurement computer performs all audio capture and DSP. Browsers receive
  low-rate telemetry, never raw audio.
- The narrow strip is the primary interface; the full dashboard is secondary.
- Keep raw fixed-microphone values visibly distinct from estimated audience-zone
  values. Never label an estimate as a measurement.
- Do not claim IEC 61672, Class 1, Class 2, regulatory, or legal compliance.
- Do not invent weighting filters or calibration math. Use authoritative
  definitions, document sources, and verify against reference signals.
- Preserve raw logs even when venue correction is enabled.
- A disconnected, clipping, uncalibrated, or stale microphone must produce an
  unmistakable UI warning.
- Do not transmit event audio or telemetry to cloud services.

## Engineering expectations

- Python service: typed code, deterministic DSP units, tests for calculations,
  and explicit sample-rate handling.
- Web client: TypeScript, responsive at an approximately 1-inch iPad window
  height, accessible colour-independent alarms, and reconnect handling.
- Ports: Vite 5173 in development; service 8000.
- Prefer small, inspectable dependencies.
- Add an ADR under `docs/decisions/` for consequential architectural changes.
- Run server tests, web tests, type checks, and production builds before commits.
- No `Co-Authored-By` trailers.

## Terminology

- `measured`: value from the fixed microphone after calibration.
- `estimated`: measured value plus a venue correction profile.
- `LAS`: A-weighted exponential Slow sound level.
- `LAeq1`: rolling 60-second A-weighted equivalent level.
- `LAeq10`: rolling 600-second A-weighted equivalent level.
- `LCpeak`: event-held C-weighted peak unless the UI explicitly states a
  different hold interval.

