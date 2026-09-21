# DSP and calibration requirements

This document defines required behaviour, not finished algorithms. No SPL value
may be presented as calibrated until these paths are implemented and verified.

## Input assumptions

- Primary device: miniDSP UMIK-1, 24-bit, 48 kHz, USB Audio Class 1.
- Input selection must bind to a stable device identifier, not whichever device
  happens to be default.
- Reject or explicitly resample unsupported sample rates.
- Track input full-scale peaks and audio callback overruns.

## UMIK calibration

- Import the serial-specific miniDSP text calibration file.
- Parse and retain its sensitivity factor and frequency/amplitude correction.
- Fixed room monitoring normally points the microphone upward and uses the 90°
  file.
- Store calibration file identity/hash with each event.
- Support a separately recorded field-calibration trim without altering the
  vendor file.
- Do not assume the REW interpretation of `Sens Factor` without verifying it
  against miniDSP/REW documentation and known acoustic levels.

## Required calculations

- A-weighted exponential Slow level (`LAS`).
- Rolling 60-second A-weighted equivalent level (`LAeq1`).
- Rolling 600-second A-weighted equivalent level (`LAeq10`).
- C-weighted acoustic peak held from event start/reset (`LCpeak`).
- Optional later metrics: `LCeq1`, `LCeq10`, C-A difference, NIOSH dose.
- 1/3-octave RTA centres from at least 25 Hz through 16 kHz.

Equivalent levels are energy averages, never arithmetic averages of dB values.
Rolling windows must behave correctly during warm-up and clearly show when a
full interval has not elapsed.

## Verification gates

Before changing mock data to `source: "umik-1"`:

1. Unit tests for weighting filters at reference frequencies.
2. Unit tests for exponential time weighting and rolling-energy windows.
3. Unit tests for peak hold and reset.
4. Synthetic sine/noise tests at multiple amplitudes and sample rates.
5. Calibration-file parser fixtures, including malformed files.
6. Comparison with REW and/or Open Sound Meter using the same UMIK and signal.
7. Comparison with a known SPL calibrator if available.
8. Long-run test for clock drift, dropped buffers, memory growth, and log gaps.

Document tolerances before running comparisons; do not choose them after seeing
results.

## Accuracy language

Allowed: “calibrated to the supplied UMIK sensitivity file,” “repeatable
operational measurement,” and “estimated audience-zone value.”

Forbidden without certified hardware and validation: “Class 1,” “Class 2,”
“IEC compliant,” “legally admissible,” or “proof of regulatory compliance.”

## Primary references

- UMIK-1 specifications and calibration:
  https://www.minidsp.com/products/acoustic-measurement/umik-1
- REW recognised USB microphone setup:
  https://www.roomeqwizard.com/betahelp/help/html/calsoundcard.html
- Open Sound Meter capabilities/manual:
  https://opensoundmeter.com/static/manuals/v1.5.pdf
- Smaart SPL metric set and calibration warning:
  https://www.rationalacoustics.com/products/smaart-spl-v9-perpetual

Obtain and cite authoritative weighting/time-response definitions during the
DSP phase. Do not copy GPL implementation code into this repository unless the
project intentionally adopts a compatible license after an explicit decision.
