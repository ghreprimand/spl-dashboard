# Roadmap

What's planned, roughly in order. Nothing here is a promise or a date. If one
of these matters to you, open an issue and say so — that's how the order gets
decided.

## Next

- **Automatic UMIK-1 calibration on macOS and Windows.** Today the cal file's
  level figure is only trusted on Linux, where the app can verify there is no
  OS gain stage between the mic and the app. The plan is to read the OS input
  volume (Windows Core Audio endpoint volume in dB; CoreAudio on macOS, where
  the UMIK-1 normally exposes no gain control) and feed it into the existing
  sensitivity formula, the same way REW does. Until then, Mac/Windows users set
  the level with a calibrator or a typed-in sensitivity.
- **Raspberry Pi verification.** It should run on a Pi 4/5 with 64-bit
  Raspberry Pi OS; nobody has confirmed CPU load and gap-free capture over a
  long event yet. Once confirmed, document it as the recommended dedicated box.

## Later

- **Sound level meter cross-check.** Compare against a certified Class 2 meter
  and publish the results. The app has matched REW on the same microphone; it
  has never been checked against a certified instrument, and the disclaimer
  will stay until it has.
- **Mixing Station integration.** There is no supported way for a third party
  to show values inside Mixing Station on iPad today. A feature request for
  read-only external values (with a stale timeout) has been raised with its
  developer. If that lands, the strip's numbers could appear inside a Mixing
  Station custom layout.
- **Android tablet workflow.** The iPad arrangement (home-screen app behind
  the mixer app) is documented and used; the Android equivalent is best-effort
  in the docs and untested.
- **Retention and archiving** of event logs (currently indefinite, manual).

## Not planned

- Certified / compliance-grade measurement. This is an operational monitor for
  the engineer, not an IEC 61672 instrument, and won't claim to be.
- Sending audio anywhere. Browsers only ever receive numbers.
- Cloud accounts, telemetry, or anything that needs an internet connection at
  the venue.
