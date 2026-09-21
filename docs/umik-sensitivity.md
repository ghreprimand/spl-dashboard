# UMIK-1 file sensitivity on direct ALSA capture

## Supported input and convention

Automatic file calibration is implemented for the legacy miniDSP UMIK-1 USB
VID/PID `2752:0007`, with its `Umik-1 Gain: NdB` descriptor, direct ALSA hardware
input, 48 kHz samples and no writable digital volume control. ALSA's read-only
channel map is permitted. Unknown devices, software/default inputs, unknown
controls, missing sensitivity, or unmatched serials do not get an automatic
SPL offset. Other microphones can use the existing explicit acoustic reference.

[Sounddevice's sample-format definition](https://python-sounddevice.readthedocs.io/en/0.5.1/api/streams.html)
sets float full scale at ±1. Our RMS dBFS is `20 log10(rms(x))`; a full-scale sine
is -3.0103 dBFS. There is no FFT amplitude or AES full-scale-sine normalization
in the broadband detector. Pressure peak uses the same absolute sample scale.

[REW author John Mulcahy's UMIK-1 conversion](https://www.avnirvana.com/threads/difference-in-dbfs-with-a-webaudio-worklet.14353/)
provides the direct-input recipe `94 + 24 - Sens Factor + 6`, with a warning that
sample/FFT conventions affect the normalization. We implement the complete
124 dB recipe on the explicit normalized PCM convention above, not a generic
94 dB USB microphone formula. This is a documented implementation convention;
synthetic tests establish its arithmetic and signal normalization, not the
physical microphone's absolute accuracy. Independent field comparison remains
pending and is displayed separately from whether calibration is applied.

The [miniDSP gain explanation](https://www.minidsp.com/community/threads/umik-1-sens-factor.9277/)
confirms that changing analog gain requires the corresponding sensitivity change.
The normal 18 dB analog gain is already included in the supplied Sens Factor.
The parser retains an optional `AGain` header; legacy files without it use the
factory 18 dB reference. Only the difference between file-reference gain and
reported hardware gain is compensated. Do not add/subtract the entire 18 dB
again when these match.

For this supported path:

```text
base offset = 124 - Sens Factor
              + file analog gain - hardware analog gain
              - applied digital gain
applied offset = base offset + field trim - correction FIR response at 1 kHz
level = weighted digital level + applied offset
```

Digital gain is zero only after direct input and the absence of a writable
volume control have been checked. The nominal 24 dB Windows digital gain in the
reference convention is not the mic's internal 18 dB analog gain. No host volume
is modified by this implementation.

The correction FIR is normalized at the 1 kHz sensitivity reference through the
last subtraction, preserving relative frequency correction while avoiding a
second absolute correction at 1 kHz. A manually entered acoustic reference
replaces the file-derived offset, and the additional field trim is then applied
once. Original calibration text is retained unchanged.

## Identity

A real USB serial must match the calibration serial (hyphens ignored). Some
UMIK-1 units report `000-0000`; this is not a unique hardware serial. Those units
are bound to a PCI controller/USB port, with an operator-confirmed physical
serial stored in settings. Moving to another port requires selecting it again.
A different unit on the same port cannot be distinguished electronically when
it reports the same placeholder; the operator must keep file and mic paired.

PortAudio discovery refreshes only while no stream is open, under a shared lock.
The sounddevice 0.5.x lifecycle functions are used to rebuild its cached device
list on first connection/retry. Active capture is never terminated by a browser
request to enumerate inputs. Reconnect health/gap behavior remains explicit.

## Presentation and evidence

`calibrated` means either supported file calibration or an explicit reference is
applied. `calibrationMethod` distinguishes `umik-file`, `reference`, `demo`, and
`none`. The UI uses FILE CAL / REFERENCE CAL and shows the applied offset and
input gains. `validationPending` remains true: no independent physical accuracy
comparison is implied. Missing calibration has an explanation, not a warm-up
countdown suggesting that waiting will produce numbers.

Tests predeclare 0.03 dB tolerance for settled synthetic 60/94/110 dB sine levels
and 0.05 dB for their C peaks. A synthetic Sens Factor of -0.250 gives offset
124.250 dB before FIR normalization/trim; -30.250 RMS dBFS maps to 94 dB. This is
an analytic test vector, not a measured calibrator result. Tests also cover
positive sensitivity, gain differences, missing/incorrect serials, unsupported
inputs/controls, explicit-reference precedence, diagnostics-only mode, and
restoring an event's absolute peak after hardware identification on restart.
