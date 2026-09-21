# ADR 0007: Responsive spectra with verified appliance cadence

Status: accepted after final 10 Hz appliance check

## Decision

Retain 4800-sample capture/broadband blocks (100 ms), and deliver genuine 10 Hz
spectra to clients. Correct the earlier 200 ms WebSocket cap (5 Hz) using 100 ms
deadline scheduling and direct model JSON serialization.

Use power-blended multiresolution spectra: 100 ms high-frequency windows through
one-/two-second bass windows. Adjacent durations are blended smoothly so static
tones at transition frequencies do not acquire an artificial level step. Stable
averaging uses elapsed samples and remains a one-second power time constant.

Use the same 2049-tap calibration FIR through SciPy FFT convolution in valid
mode over current input plus the preceding 2048 input samples. Coefficients,
causal delay and output length stay identical within floating-point tolerance.
Verify against direct lfilter across noise/impulse block boundaries with absolute
1e-12 / relative 1e-10 tolerance. This changes computation, not the filter.

Precompute fractional-cell weights and vectorize local band reductions, avoiding
both Python-loop overhead and subtractive cancellation beside strong tones.
Run history JSON extraction in a worker with its own read-only SQLite connection;
the writer connection stays on the capture event loop. Full logs are preserved.

## Trial evidence and tradeoff

A 2400-sample callback / nominal 20 Hz trial delivered approximately 19.5 distinct
spectra per second. Initial versions saturated one core and dropped buffers.
Optimizations produced a short gap-free interval, but an extended check still
found an overrun. Reject the higher rate rather than calling that reliable.
Retain the useful response-time and CPU improvements at 10 Hz. Trial interruptions
remain recorded in the active event; never erase them to make a test look clean.

Capture continuity and recording take priority over analyzer frame rate. A
future 20 Hz mode needs new hardware evidence or further scheduling improvements.

The final one-minute trial delivered 9.98 distinct spectra/s with gap count
105 -> 105, no overruns and 77.6% of one core used under recording/history load.
History responses sometimes took 724 ms but no longer blocked capture. This
is a short acceptance check, not a multi-hour soak.
