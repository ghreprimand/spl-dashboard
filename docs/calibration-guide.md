# Calibration guide

Calibration is what turns the microphone's raw electrical level into a real
sound-pressure level in decibels (dB SPL). Until a calibration is applied, the
dashboard shows input diagnostics (raw dBFS, spectrum, health) but no SPL
numbers — waiting does not make them appear.

This guide helps you pick the right mode for your microphone and setup. All of
these settings live in **Input & calibration** in the admin console.

> **What "calibrated" means here.** It means a calibration has been *applied*.
> It does **not** mean the reading has been independently verified against a
> certified sound level meter. SPL Dashboard is an operational monitor, not a
> compliance meter. See the disclaimer in the README.

## The four modes

| Mode | Badge on the strip | Use it when |
| --- | --- | --- |
| Automatic UMIK-1 calibration file | `FILE CAL` | You have a miniDSP UMIK-1 plugged directly into a **Linux** computer |
| Known-level acoustic reference | `REFERENCE CAL` | You have a calibrator or a known-SPL source you can play into the mic |
| Manual sensitivity (dBFS at 94 dB SPL) | `MANUAL CAL` | You know the microphone's sensitivity figure but have no calibrator to hand |
| Input diagnostics only | *(none)* | You only want the spectrum and level activity, not absolute SPL |

## Which setup is for me?

### A UMIK-1 on a Linux computer

Use **Automatic UMIK-1 calibration file**.

1. Plug the UMIK-1 in and choose it under **Microphone**.
2. Load the calibration file that came with your microphone (the file whose
   name contains your microphone's serial number). Use the file for the
   orientation you are using (miniDSP ships a 0° and a 90° file).
3. If the serial in the file matches the microphone, the strip shows `FILE CAL`
   and SPL readings appear.

*Caveat:* the sensitivity in that file is miniDSP's factory figure. The app
applies it exactly and normalises the frequency response, but the absolute
result has not been checked against a certified meter.

### A UMIK-1 (or UMIK-2) on macOS or Windows

Automatic mode only works for a UMIK-1 on direct Linux input, so on macOS and
Windows automatic mode will tell you it needs a direct UMIK-1 input. That is
expected. Instead:

- Still **load the calibration file** — it corrects the frequency response.
- Then set the level with either **Known-level acoustic reference** (best, if
  you have a calibrator) or **Manual sensitivity** using the file's Sens Factor
  (see below).

*Caveat:* on macOS and Windows the operating system's input-volume slider
changes the digital level. Set it once, note it, and do not change it after
calibrating.

### Any USB microphone with a calibrator

Use **Known-level acoustic reference**. A calibrator produces a known level
(usually 94 dB SPL, sometimes 114 dB) at 1 kHz.

1. Choose your microphone and, if you have one, load its frequency-response file.
2. Fit the calibrator over the microphone and switch it on.
3. Open the reference section and click **Capture raw RMS now**. The app measures
   its own raw dBFS for about five seconds and fills in *Observed raw RMS*.
4. Enter the calibrator's level in *Known reference level* (e.g. 94), write a
   note (equipment, date, input gain), and apply.

*Caveat:* the reading is only as good as the calibrator and as stable as your
input gain. If you change the gain afterwards, recalibrate.

### Any microphone next to a sound level meter

Use **Known-level acoustic reference**. Put the meter and the microphone close
together in a steady sound field (a test tone works well).

1. Read the level on the meter.
2. Click **Capture raw RMS now** (or type the *Observed raw RMS* shown under
   Input health).
3. Enter the meter's reading as *Known reference level*, add a note, and apply.

*Caveat:* this transfers the other meter's accuracy and its position to this
app. Keep the two microphones close and the field steady.

### You know the sensitivity but have no calibrator

Use **Manual sensitivity**. Enter the raw RMS the microphone produces at
94 dB SPL, in this app's dBFS scale. For a miniDSP microphone this is the
**Sens Factor** from its calibration file (a value like `-30.2 dB`). Add a note
recording the audio interface and the OS input gain, then apply. The strip shows
`MANUAL CAL`.

*Caveat:* this depends entirely on the sensitivity figure being correct for your
exact input gain. On macOS and Windows the OS input-volume slider changes the
digital level and invalidates the entered value — set it, note it, leave it.

### No reference at all

Use **Input diagnostics only**. You still get the spectrum analyzer (in dBFS),
clipping and input-health warnings, and can watch relative level changes — just
not absolute dB SPL.

## Full-scale convention

This app uses `RMS dBFS = 20·log10(rms)`, so a full-scale sine reads −3.01 dBFS.
Other applications sometimes use a different full-scale convention; do not paste
another app's dBFS value into the reference field without accounting for that.
Use **Capture raw RMS now** to read this app's own value instead.

## History

The separation between *applying* a calibration and *independently validating*
it is deliberate. See
[ADR 0003 — File calibration and independent field validation are separate](decisions/0003-umik-file-calibration.md)
and the [UMIK sensitivity conventions](umik-sensitivity.md) for the arithmetic.
