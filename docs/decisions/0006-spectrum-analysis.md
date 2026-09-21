# ADR 0006: Explicit band-energy analysis and display controls

Status: accepted; supersedes ADR 0004's single-resolution FFT implementation.

The analyzer uses one-second windows for 1/3 and 1/6 bands and two-second windows
for 1/12 detail. Every 100 ms it emits complete-window band energies and a
separate one-second exponential power average. Fractional FFT-cell integration
reduces hard boundary quantization. No partial spectra are drawn during startup.

A separate raw-PCM spectrum path applies the normalized microphone file curve
in the frequency domain. This avoids the broadband FIR's low-frequency
approximation. Absolute normalization is recovered explicitly at 1 kHz; no
second calibration or audience offset is applied. A/C meter DSP stays unchanged.

The client defaults to 1/6 band steps with a 60 dB view range. Band detail,
averaging, line/steps and vertical range persist per browser. Local freeze,
cursor and dashed maxima do not alter server measurements. Live versus stale,
clipping, warming and off-scale conditions are explicit. Analysis identities
reset holds after capture/configuration changes.

The payload retains legacy third-octave/detail fields for existing clients;
new band sets carry actual edges, analysis duration and readiness. History
continues to return compact chart data so larger spectra cannot stall capture
through repeated full-history serialization. See spectrum-analyzer.md for
sources, equations, limits and verification.
