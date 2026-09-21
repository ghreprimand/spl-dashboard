# Hardware acceptance and verification status

## Verification status

Absolute levels have been compared against REW on the **same microphone** with
matching results. They have **not** been independently verified against a
certified sound level meter, and there is no plan to pursue certified
verification. SPL Dashboard is an operational monitor, not a compliance meter;
use your own judgement and your own reference for anything that matters.

The procedure below is a **confidence exercise** you can repeat on your own gear,
not a gating certification. Record the host model, OS version, microphone serial,
calibration file hash/orientation, USB connection, OS input gain, reference
software version/settings and test date so results are reproducible.

## 1. Prove input and isolation

1. Boot the appliance with the microphone attached. Open the setup page and
   select its USB-serial-bound entry. Confirm the expected 48 kHz channel.
2. Before loading a file, expect UNCALIBRATED/UNVERIFIED, raw RMS/peak dBFS,
   FFT activity and unavailable SPL metrics. Then load the correct file with
   automatic calibration selected; a supported UMIK-1 should show FILE CAL and
   SPL readings immediately. Separate reference fields can stay blank.
3. Unplug the mic. Expect MIC LOST/STALE within approximately two seconds.
   Reconnect it; only the selected device may resume. Verify gap count and
   averaging warm-up restart. A different microphone must not substitute itself.
4. Confirm input gain is fixed and no AGC/noise suppression is enabled. Compare
   input dBFS against reference software, allowing for different full-scale RMS
   conventions (this app gives -3.0103 dBFS for a peak-full-scale sine).
5. Exercise clipping with a synthetic near-full-scale WAV, not an unnecessarily
   loud acoustic signal. Expect CLIPPING and nonzero clipped sample duration.

## 2. Compare calibration and DSP

1. Load the correct vendor calibration file. Confirm serial and file hash.
2. Use a stable 1 kHz reference. A suitable acoustic calibrator is preferable;
   an established, configured UMIK reference application can provide a comparison
   without claiming an independent physical calibration. Record which was used.
3. Record known SPL and this app's raw RMS dBFS at unchanged gain. Compare file
   calibration first with field trim zero. If establishing an explicit reference,
   enter these values plus equipment/gain notes. Do not paste
   another application's dBFS value into this app's reference field.
4. Compare stable 1 kHz levels at several amplitudes. Target agreement within
   1 dB. Then compare stable broadband A-weighted levels within 1.5 dB. Match
   frequency calibration, weighting, gain, time constants and Leq intervals.
5. Wait for full 60 s / 600 s windows before full-window comparisons. Test rising,
   falling and interrupted signals. Reset peak after settling to compare a
   steady sine; switch-on transients are legitimately held by the peak detector.
6. Test LCpeak separately with matched C weighting and reset/hold intervals;
   document signal and tolerance before comparison. Do not compare it to an
   unweighted or Slow maximum and call the difference an error.
7. Investigate discrepancies rather than changing tolerances or adding an
   unexplained trim. Remember this is a comparison against another application
   (such as REW) on the same microphone, not a certified-meter verification.

## 3. Verify event durability and failure presentation

1. Start a named event. Open two browsers; they should agree.
2. Close both for several minutes. Reopen and export: logging must continue.
3. Add an annotation, reset peak, export CSV and JSON; inspect timestamps,
   raw/estimated columns, calibration identity and annotation order.
4. Restart the service during the event. The same event must resume with a
   restart annotation and gap counter. Windows restart; the last durable peak
   returns. There may be up to one logging interval of uncommitted data loss.
5. Unplug/replug USB and temporarily disconnect LAN. Confirm explicit health
   warnings, reconnection and warm-up. Network loss must not cause audio gaps.
6. Run a multi-hour test on the intended computer. Check overrun counts, process
   memory, CPU load, disk growth and the exported timestamp gaps. This cannot be
   replaced by the accelerated synthetic DSP soak.

## 4. Test the intended iPad workflow

1. Open `/display` alongside Mixing Station. Adjust width, height, digits,
   spacing and placement. Check legibility at the actual minimum window size.
2. Reopen/reload and confirm that layout persists. Another browser may use a
   different layout without changing the iPad's display.
3. Test the ellipsis settings control in a shallow window, portrait/landscape,
   sleep/wake, and Wi-Fi reconnect. No stale values should look live.
4. Turn off the router's WAN connection, then cold-boot the appliance. Open the
   UI over the event LAN and confirm full operation without external services.

Record results and discrepancies in a dated test artifact, including exported
records. These checks build confidence for your own deployment; they are not a
certified-meter verification and none is claimed.
