# Spectrum analyzer: definition and validation

This is a calibrated, unweighted FFT band-energy RTA at the fixed microphone.
It is not a transfer function, a standardized octave filter bank, or an audience
spectrum estimate. No raw audio reaches the browser.

## Definitions

Analysis uses 48 kHz PCM in 100 ms capture blocks (10 updates/s). Broadband
meter time constants and Leq integration are unchanged. A 20 Hz trial was
rejected after capture overruns on the NUC. Spectrum windows are 0.1, 0.25, 0.5, 1 and 2 seconds. Each band
selects adjacent durations around six FFT bins per band width, blending their
**powers** by logarithmic duration. This smooth transition avoids a step in
window behavior between neighboring bands. Broad/balanced views cap at one
second; fine detail caps at two seconds. Upper bands use 100 ms windows; bass
retains longer windows. A complete longest window is required before displaying
a resolution. These are multiresolution estimates: transient bands represent
different time spans, not one simultaneous broadband energy measurement.

Centres cover nominal 20 Hz–20 kHz, using the base-ten octave approximation
anchored at 1 kHz. Outer band edges extend beyond nominal centre labels and
remain below Nyquist. No IEC geometry/conformance claim.

One-sided bin energy is `abs(rfft(x*w))² / (N*sum(w²))`, doubled except at DC
and Nyquist. This equals periodogram density times bin width. Each bin's energy
is spread uniformly across its cell (centre ± half-bin); local power sums
allocate fractional cells at band edges without subtractive cancellation. Adjacent bands conserve energy. This
reduces boundary quantization for noise but does not undo spectral leakage or
resolve two tones inside a window's main lobe.

Raw PCM feeds this separate analyzer. The calibration file response is
interpolated in log frequency, negated and normalized at 1 kHz. Its power gain
is applied once to FFT bins. The acoustic offset recovers the broadband path's
pre-FIR offset by adding back the implemented FIR's 1 kHz gain. Thus a flat
file response does not cause a second absolute correction. Without an absolute
reference the graph reports dBFS, with relative file correction if supplied.
The existing A/C meter filters, calibration convention and logs are unchanged.

Live window shows the current band energies. Stable adds a one-second
exponential **power** average at the 100 ms hop, initialized with the first
complete window. It is not a 125 ms Fast detector. Actual display latency includes
the analysis window. Browser easing (60 ms, disabled for reduced motion) is
cosmetic. Gaps/configuration changes create a new analysis identity, resetting
window/average state and local display holds.

## Display

Default: 1/6-octave steps, live window, 60 dB range, top 100 dB SPL. A separate
relative dBFS top is shown when uncalibrated. Controls persist per browser.
Steps span real band edges; optional lines join band centres and are not
additional measurements. Missing values break traces, never fabricate floor
energy. Off-scale, warm-up, stale and clipping are explicit. Tap/arrow navigation
shows band bounds and levels. Freeze and dashed band maxima are local visual
controls, separate from LCpeak and measurement logging. Clipped/stale input is
not added to the local maxima. Changing analysis settings resets local holds.

## Reference basis

- [REW RTA](https://www.roomeqwizard.com/help/help_en-GB/html/spectrum.html):
  band power differs from FFT-bin amplitude, Hann trades leakage for resolution,
  complete windows and overlap are distinct from temporal averaging.
- [SciPy periodogram](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.periodogram.html):
  one-sided power density scaling and window normalization.
- [Rational Acoustics banding](https://support.rationalacoustics.com/support/solutions/articles/150000185133-banding-vs-smoothing):
  band energy is summed power, not smoothed transfer-function magnitude.
- [Rational Acoustics temporal averaging](https://support.rationalacoustics.com/support/solutions/articles/150000214542-averaging-over-time-temporal-averaging-):
  stability and response speed must be chosen deliberately.

## Verification gates

Before deployment: compare bin normalization with independent SciPy periodogram
and band integration with direct per-cell overlap summation (relative tolerance
1e-10); verify geometry and conservation across bin/band edges; preserve the
existing 0.03 dB centred 1 kHz tone tolerance; verify the coherent 25 Hz Hann
three-bin prediction within 0.003 dB; verify flat calibration cancellation and
relative correction within 0.05 dB for adequately resolved tones. Test silence,
full-window readiness, source reset and the analytical exponential power-average
recurrence. Validate pink/white-noise trends separately from tone amplitudes.

Physical REW band-by-band comparison remains pending. The earlier broadband
A/Slow comparison does not validate the spectrum. Do not invent a fixed bass
offset from a single tone's leakage error. Benchmark the NUC with recording and
history polling active; retain raw logs and mark deployment gaps.


## Cadence correction in 0.4.1

The earlier analyzer computed at 10 Hz but the WebSocket still waited 200 ms
between sends (5 Hz). The shipped 0.4.1 path computes and sends at 10 Hz using
100 ms deadlines and direct Pydantic JSON serialization. The 20 Hz trial reached
approximately 19.5 distinct browser spectra per second but showed intermittent
overruns under recording/history load, so it was rejected. Multiresolution
windows, FIR computation and history optimizations are retained at 10 Hz.
Validate actual browser sequences rather than inferring rate from a heartbeat.
