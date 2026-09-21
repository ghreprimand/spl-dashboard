# ADR 0004: Smooth spectrum telemetry and plain-language metric labels

Status: accepted

The server computes one-second Hann FFT band energy every 100 ms and publishes
10 Hz telemetry. Preserve third-octave values and add a 1/12-octave trace using
the same window-energy normalization. No raw audio reaches browsers.

Canvas draws a logarithmic frequency axis, fixed level scale and an animated
curve. An 80 ms display interpolation is cosmetic, not extra measurement data.
A tap opens a larger labelled analyzer. Disconnection freezes and marks the
trace stale. The one-second analysis window still limits transient response;
this is not a transfer-function tool or certified fractional-octave filter bank.

Primary metric labels are Live level, 1-minute average, 10-minute average and
Peak since reset. Technical names, weighting and time response remain in the
secondary descriptions. Calculations and export field names are unchanged.
