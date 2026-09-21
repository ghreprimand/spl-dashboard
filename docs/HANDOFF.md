# Build handoff

This document describes the **current** state of the appliance at version 0.4.4
(public source snapshot). It is self-contained: read it top to bottom for the present
behaviour. The **Version history** at the end is retained for context only and
is explicitly superseded where it disagrees with the sections above.

## Current state (0.4.4)

Hardware-test beta. The appliance runs one shared capture/DSP runtime with:

- Explicit USB device selection (serial-bound or physical-port-bound), local PCM WAV replay, and a
  clearly labelled generated demonstration input.
- Input health (connected / stale / clipping / gap / overrun), calibration-file
  parsing and correction, and reference-based A/C weighting.
- Broadband metrics: `LAS` (A Slow), `LAeq1` (60 s), `LAeq10` (600 s), `LCpeak`
  (C-weighted peak held from event/reset) and **maximum live level** (`lasMaxDb`).
- A multiresolution FFT spectrum analyzer (see below), not a single fixed trace.
- SQLite event logging, annotations, peak/maximum reset, CSV and JSON export,
  and restart recovery.
- A durable audience-mapping library with a shared reading location and an
  explicit clear action (see below). A-only venue offsets preserve raw records
  and produce separately labelled estimates.
- Configurable thresholds, disabled by default, applied to raw fixed-mic values.

The primary `/display` strip shows five metrics plus a compact spectrum trace
and health. Strip width, height, digit size, spacing and position are
browser-local; full setup is reachable through the strip's ellipsis control,
including in a shallow viewport. iPadOS owns external window placement.

## Strip metrics

Left to right the strip shows Live level (`LAS`), Maximum live level (`lasMaxDb`),
1-minute average (`LAeq1`), 10-minute average (`LAeq10`) and Peak since reset
(`LCpeak`), with the technical names retained beneath the friendly labels.
`lasMaxDb` is the highest A-weighted Slow value evaluated on the service's 100 ms
boundaries since input/event start or its own reset — independent of C peak, and
not a pressure peak. The arrow beside Peak resets its hold without needing an
active event. Both holds survive gaps and active-event restart; no maximum is
invented for older records (their new CSV column is left blank). Input health
reads USB MICROPHONE rather than exposing the internal `umik-unverified` enum.

## Spectrum analyzer (current)

A separate raw-PCM, unweighted FFT band-energy RTA at the fixed microphone. It is
not a transfer function, a standardized octave filter bank, or an audience
estimate. Details and validation gates live in
[`spectrum-analyzer.md`](spectrum-analyzer.md) and ADR
[0006](decisions/0006-spectrum-analysis.md)/[0007](decisions/0007-analyzer-cadence.md).

- Computed and delivered at **10 Hz** (100 ms hop). The earlier 5 Hz WebSocket
  cap and a rejected 20 Hz capture trial are historical (see below).
- **Multiresolution** windows of 0.1, 0.25, 0.5, 1 and 2 s: upper bands use short
  windows for fast response, bass retains longer windows, and adjacent durations
  are power-blended so a static tone at a transition frequency shows no step.
- Publishes three band sets each frame — 1/3, 1/6 and 1/12-octave (base-ten,
  anchored at 1 kHz), plus backwards-compatible flat 1/3-octave (25 Hz–16 kHz)
  and detail-trace fields for older clients and exports.
- Nominal coverage 20 Hz–20 kHz. The browser default view is **1/6-octave**;
  band steps, joining line, level range, freeze, cursor and local maxima are
  browser-local controls. dBFS until an acoustic reference or file calibration
  supplies dB SPL.

## Audience mapping (current)

- **Guided capture:** fixed mic position, three audience positions, return check.
  Each button captures 30 s of host A-weighted energy and rejects clipping,
  input gaps and fixed-check drift over 2 dB. Only a single A-weighted offset is
  produced; there is no C or per-band correction curve.
- **Shared reading location (ADR 0008):** the audience/measured choice persists
  on the appliance and travels in telemetry, so all clients agree. The obsolete
  browser-local audience flag is ignored. Toggling only the reading location does
  not restart capture or averaging.
- **Durable library (ADR 0009):** applied mappings are content-hashed snapshots
  in an additive `audience_mappings` table (name, correction, capture note,
  date). Select/apply, sort by name/date/correction, and confirmed deletion of
  inactive profiles. The active mapping migrates in idempotently at startup.
- **Clear (0.4.4):** `POST /api/audience-mapping/clear` unloads the profile on
  all clients without deleting the saved copy, so even the only saved mapping can
  then be deleted. Applying, activating and clearing restart averaging windows
  and are blocked while recording; loaded profiles are protected from deletion.
  Historical event configurations keep their original mapping.

## Calibration and sources of truth

Supported direct UMIK-1 capture applies the supplied sensitivity file and shows
FILE CAL; the device/gain gates and conversion are in
[`umik-sensitivity.md`](umik-sensitivity.md). A manual acoustic reference is
optional and takes precedence (REFERENCE CAL). `status.calibrated` means a
supported file conversion or explicit reference is applied — not independent
physical validation, which remains pending and is surfaced separately as
`validationPending`. The hardware source remains `umik-unverified` in this release; a field comparison
alone does not automatically change that enum. Equations, reference sources, numerical conventions and predeclared
tolerances are in [`dsp-implementation.md`](dsp-implementation.md).

## Known boundaries and limitations

- USB capture has been exercised on the NUC5CPYH and a UMIK-1; absolute acoustic
  accuracy is not yet independently validated.
- FFT band energy is a visualization, not a certified octave filter bank; no IEC,
  Class 1/Class 2 or regulatory claim is made.
- Demo and WAV are clearly separate input modes. No raw event audio is recorded,
  uploaded or sent to browsers.
- A home-screen manifest is provided; a browser service-worker PWA is **not**
  implemented (plain LAN HTTP).
- No user authentication: operate on a trusted event LAN. Same-origin browser
  mutation protection exists but is not authentication.
- Retention is indefinite; no automatic deletion and no report PDF. There is no
  bulk mapping-library export/import API — back up `events.sqlite3` itself.
- Event pause is not implemented. Stop preserves an event; start creates another.
- `summary.json` is event metadata only; full per-frame telemetry is in SQLite;
  CSV exports only selected scalar fields. The CSV has no estimated-LASmax column even though the frame can hold
  one.
- Service restart retains the active event and durable peak/maximum but restarts
  averaging windows and records a gap; the last uncommitted logging interval may
  be lost.

## Test evidence

`make check` runs server tests, web tests, ruff lint, mypy types and the web
build. Current baseline: **100 server tests and 18 web tests pass**. Server tests
exercise reference calculations, weighting/time constants, rolling energy
windows, peak/maximum hold, calibration parsing (including malformed files and
gain gates), WAV formats, the shared runtime, event persistence and restart
recovery, raw/estimated separation, the mapping library (migration, dedup,
same-name versions, activation, recording guards, protected-profile deletion,
clear) and the spectrum analyzer's numerical gates. Web tests cover warnings,
reconnect behaviour, schema validation, saved layout controls and the clear
button. CI (`.github/workflows/ci.yml`) runs pytest + web test + web build on
Python 3.12 / Node 22; lint and type checks run locally via `make check`.

## Deployment baseline and next steps

The appliance is deployed to the NUC as a built **wheel** (not an editable
checkout); see [`deployment.md`](deployment.md) for the current wheel build,
offline upgrade, SQLite backup and rollback procedures. The NUC is provisioned
and its automatic UEFI boot has been verified. 0.4.4 is deployed and its automated
suite passes, but this is a bench/software baseline, **not** field validation.

Run the remaining checks in [`hardware-acceptance.md`](hardware-acceptance.md):
independent absolute SPL comparison, band-by-band spectrum comparison, multi-hour
capture soak, iPad window behaviour and offline cold boot. Do not mark real SPL
complete merely because plausible numbers appear.

## Later product work

After hardware evidence: decide authenticated shared-LAN operation, an
archive/retention policy, a preferred event report format, and a bulk
mapping-library export/import. Refine iPad placement only after measuring the
actual attainable window constraints. An operator reported the strip remained visible
behind a resized Mixing Station for several minutes; a formal iPad workflow test
is still outstanding, and picture-in-picture was never shipped.

---

## Version history (historical — superseded by the sections above)

These notes record how the current behaviour was reached. Where they conflict
with the current sections, the current sections win.

- **Analyzer 0.4 (superseded by "Spectrum analyzer" above):** introduced nominal
  20 Hz–20 kHz coverage, 1/3 / 1/6 / 1/12 detail, complete one-/two-second
  windows, fractional-bin integration, direct normalized frequency-domain file
  correction and power-domain stable averaging, replacing the former fixed 1/12
  trace. Default browser view became 1/6. ADR 0006. NOTE: an earlier draft
  described "113 fixed 1/12-octave bands with a one-second window" — that is
  obsolete; the analyzer now uses multiresolution windows and publishes three
  band sets.
- **Analyzer cadence 0.4.1 (superseded, folded into 10 Hz above):** the 20 Hz
  capture trial was rejected after intermittent NUC overruns; the shipped path
  computes and sends 10 Hz spectra (the previous WebSocket had been capped at
  5 Hz despite 10 Hz DSP). Multiresolution windows, vectorized band reductions,
  equivalent FFT calibration filtering and read-only history workers reduced load;
  trial gaps/annotations remain in the recording rather than being erased.
- **Shared audience display (ADR 0008, current):** replaced the browser-local
  reading location with a server-owned, telemetry-published choice.
- **Mapping library 0.4.3 (ADR 0009, current):** added the durable SQLite mapping
  library with sorting and confirmed deletion; the existing active mapping
  migrated without changing its captures or timestamp.
- **Clear loaded mapping 0.4.4 (current):** added the explicit unload action.
