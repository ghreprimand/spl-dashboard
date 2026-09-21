# DSP implementation and predeclared verification tolerances

This implementation is a hardware-test beta. It does not claim IEC or class
compliance. No input becomes `umik-1` in this release. Hardware gain, serial
binding, long-run capture and absolute agreement remain acceptance gates.

## Definitions and sources

- [Cross-Spectrum frequency weighting equations](https://www.cross-spectrum.com/audio/weighting.html):
  published A/C analog transfer functions, using poles at 20.6 and 12200 Hz,
  with 107.7 and 737.9 Hz additionally for A. Normalization is at 1 kHz.
- [Brüel & Kjær 2250 manual, section 2.9](https://www.bksv.com/media/downloads/2250/be1712.pdf):
  exponential averaging of squared weighted pressure, Slow time constant 1 s,
  reference pressure 20 µPa.
- [FHWA noise measurement handbook](https://www.fhwa.dot.gov/ENVIRonment/noise/measurement/handbook.cfm):
  equivalent level is the logarithm of mean-square pressure relative to the
  reference pressure squared.
- [REW calibration files](https://www.roomeqwizard.com/help/help_en-GB/html/calfiles.html):
  calibration pairs describe microphone response and are subtracted; sensitivity
  interpretation also depends on device gain. Supported UMIK-1 inputs now use
  the explicit conversion in [UMIK sensitivity](umik-sensitivity.md).
- [miniDSP UMIK-1](https://www.minidsp.com/products/acoustic-measurement/umik-1):
  serial-specific files and orientation options.
- [SciPy bilinear transform](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.bilinear_zpk.html):
  the transform does not prewarp automatically. Using a higher internal rate
  reduces high-frequency warping; it does not establish standards compliance.

## Signal path

Only 48 kHz input is accepted. Capture is mono, explicitly selected channel,
4800 samples per block (100 ms). Samples are normalized to digital full-scale
peak 1. Raw RMS dBFS is `10 log10(mean(x²))`; a full-scale sine is -3.0103 dBFS.
This convention must be accounted for when comparing other software meters.
Raw peak is `20 log10(max(abs(x)))`. Silence is JSON null, never infinity.

Vendor response is interpolated in log frequency and negated, then implemented
as a 2049-tap linear-phase FIR. Response is held constant beyond supplied
endpoints. Files with corrections outside ±30 dB are rejected for inspection.
This FIR is an approximation, particularly at low frequencies; verify the
actual serial-specific curve before using it at an event. Its delay is 21.33 ms.

For A/C weighting, a stateful 161-tap Kaiser interpolation filter upsamples by
four to 192 kHz, followed by bilinear analog weighting filters in second-order
sections. States persist across blocks. No blockwise independent resampling.
Slow operates sample-by-sample on A-weighted squared samples. The 60 s and
600 s windows accumulate mean-square energy for exactly 600 and 6000 blocks.
They report partial elapsed windows while warming. LCpeak holds the largest
absolute C-weighted internal sample from event start/reset. It is not an
exponential or block RMS peak, and no true-peak or transient calibration
accuracy claim is made.

A gap resets filter and averaging state, retains the event peak, increments a
visible gap counter, and makes the missing interval explicit. It does not add
silence to Leq. After restart, peak restores from the last durable one-second
record; up to one logging interval may have been lost. Warm-up restarts.

The RTA is a **separate raw-PCM** unweighted FFT band-energy analyzer, refreshing
ten times per second. It uses **multiresolution** Hann windows (0.1, 0.25, 0.5, 1
and 2 s), power-blended per band so upper bands respond quickly while bass keeps
longer windows, and it publishes 1/3, 1/6 and 1/12-octave band sets (base-ten,
nominal 20 Hz–20 kHz). It applies a normalized frequency-domain calibration
correction independent of the A/C broadband path. It is an unweighted FFT band
estimate, not a standardized octave filter bank, and reports dBFS until an
acoustic reference or file calibration supplies dB SPL. Full definitions,
geometry, conservation and verification gates are in
[spectrum-analyzer.md](spectrum-analyzer.md); see also ADR 0006/0007.

## File calibration and optional absolute reference

Supported direct UMIK-1 inputs use the sensitivity file automatically. See
[UMIK sensitivity](umik-sensitivity.md) for the exact device/gain gates and
normalization. A separate acoustic reference is optional and takes precedence.


The operator supplies a stable 1 kHz reference level and the raw RMS dBFS
observed by this app, with input gain and equipment recorded. Offset is:

`reference SPL - raw RMS dBFS - correction response at 1 kHz + field trim`.

The correction term uses the implemented FIR response, avoiding double
correction at the reference frequency. This reference is only valid for the
same device, channel and gain. UI input/file changes clear reference fields.
The API accepts an explicitly supplied reference with its configuration.
`status.calibrated` means a supported file conversion or explicit reference is
applied, not independent physical validation. `validationPending` remains true
and is explained separately in input health; the strip shows FILE CAL or
REFERENCE CAL.

Demo uses a deliberately fictitious 128 dB offset and is always labelled DEMO.
WAV input remains labelled WAV REPLAY and requires a separate explicit level
reference. Automatic vendor scaling is limited to the verified direct ALSA input
profile described in the sensitivity document.

Audience profiles currently support a named A-weighted offset supplied from
venue mapping. Estimates are separate A metrics; no audience LCpeak is inferred.
All raw metrics, flags and calibration identity remain in the durable record.

## Automated tolerances (set before test execution)

- A/C response: within 0.35 dB of the published analog equations at 25, 31.5,
  63, 125, 250, 500, 1000, 2000, 4000, 8000, 12500 and 16000 Hz.
- Settled 1 kHz sine: equivalent level within 0.03 dB; Slow after 10 seconds
  within 0.03 dB; C peak within 0.05 dB of analytic amplitude scaling.
- Deterministic broadband noise: A-weighted mean-square level within 0.2 dB
  of independently weighted full-record FFT energy (ten seconds).
- Amplitude changes: 20 dB per factor ten within 0.01 dB.
- Exponential step response: within 1e-9 of `1-exp(-t)` in squared units.
- Rolling energy: analytic mean-square average within 1e-10, exact block expiry.
- Flat frequency calibration: within 0.03 dB after settling.
- RTA 1 kHz sine band: within 0.03 dB of analytic RMS energy.
- Unsupported sample rates, non-finite samples and malformed calibration reject.

Hardware comparison target, to be tested rather than claimed: agree within
1 dB on stable 1 kHz levels and within 1.5 dB on broadband A-weighted levels
against configured reference software. Investigate disagreement instead of
adjusting tolerances after the fact. Transient peak comparisons need separate
signals and matching weighting/hold definitions.

Each frame carries 1/3, 1/6 and 1/12-octave band sets from the same normalized
FFT; the detail curve uses the 1/12 values and flat 1/3-octave values remain
available for older clients and exports. Longer windows (up to 2 s) give finer
bin spacing once filled; narrow low-frequency bands still have few bins and are
FFT estimates, not filter-bank outputs. See
[spectrum-analyzer.md](spectrum-analyzer.md) for the multiresolution window
schedule and per-band coverage.

## Maximum live level

`lasMaxDb` holds the maximum calibrated LAS evaluated at each 100 ms capture
boundary, independently of the browser refresh rate. It is the maximum of the
same Slow energy detector as Live level, not a pressure peak or Leq value.
It is not advertised as a sample-exact standardized LASmax detector. It resets
on input configuration/event start or the separate reset-maximum action;
reconnections preserve it. Active-event restart restores its last durable value.
Older records have no value; CSV leaves their new column blank. LCpeak and its
reset remain independent. The strip displays five metrics.

## Spectrum change history (0.4)

Changelog only; the current analyzer behaviour is described in the signal-path
section above and in [spectrum-analyzer.md](spectrum-analyzer.md). 0.4 replaced
the original single fixed-window RTA with the separate raw-PCM frequency-domain
calibration path, multiresolution windows and selectable fractional-octave bands.
A/C broadband filters and level calibration were unchanged.

## Capture cadence and FIR computation (0.4.1)

Capture retains 4800 samples every 100 ms; all integration periods remain
unchanged. A 2400-sample/20 Hz trial was rejected after appliance overruns. The calibration FIR uses
[SciPy FFT convolution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.fftconvolve.html)
in valid mode on 2048 history samples plus the new 4800 samples. This yields
exactly the causal block output with unchanged coefficients and delay, up to
floating-point roundoff. Rebuilds clear input history at gaps. Direct-FIR
comparison tolerance is 1e-12 absolute / 1e-10 relative across block boundaries.
