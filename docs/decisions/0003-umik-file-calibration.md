# ADR 0003: File calibration and independent field validation are separate

- Status: accepted
- Date: 2026-09-20
- Supersedes ADR 0002's requirement for a manually entered reference to show SPL.

## Decision

A supported UMIK-1 on direct ALSA capture uses its Sens Factor automatically,
with explicit sample normalization and observed hardware gain/controls. Store
calibration method, version, gain and applied offset alongside every raw record.
A manually supplied acoustic reference overrides automatic conversion; an off
mode supports diagnostics. Do not rewrite earlier records when calibration changes.

Require electronic serial agreement or operator confirmation where the USB serial
is a placeholder. Bind those devices to their physical USB port, not a fabricated
unique serial. Refresh PortAudio's cached enumeration only when no stream is open.

Show FILE CAL when the file is applied, and explain pending independent field
comparison separately. Missing calibration must not look like a warm-up wait.
The user should not need another measurement application for normal startup.

## Rationale and consequences

The earlier UI hid values after a correct file had been loaded because it only
supported explicit reference levels. That conflated applying manufacturer
calibration with independently validating it. Both states matter and are now
represented separately. Physical accuracy comparisons remain a development and
acceptance responsibility, not a prerequisite for file-calibrated operation.
The source remains `umik-unverified` until the existing validation gates pass.
Equations, source attribution, supported hardware limits and test conventions
are documented in `docs/umik-sensitivity.md`.
