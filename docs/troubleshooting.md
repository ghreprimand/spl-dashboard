# Troubleshooting

Quick fixes for the most common problems. If a symptom isn't here, check
[Input health](getting-started.md) in the admin console — it usually says what's
wrong in plain language.

## No input devices are listed

- Make sure the microphone is plugged in **before** you start the app, or restart
  the app after plugging it in.
- **Linux:** the audio library may be missing — see the next item.
- Close other apps that might be holding the microphone exclusively.
- Check your operating system's privacy/permissions settings allow microphone
  access for the terminal or the app.

## "libportaudio" missing (Linux)

On Linux the PortAudio runtime is a separate system package. Install it:

```bash
sudo apt install libportaudio2      # Debian/Ubuntu
```

On other distributions install their PortAudio runtime package. macOS and Windows
do not need this — PortAudio ships with the app there. The generated demo and WAV
replay work without it; live microphone capture does not.

## Wrong sample rate

The app runs at 48 kHz. If your microphone or interface is set to another rate:

- Set the device to 48 kHz in your operating system's sound settings.
- For WAV replay, the file must be 48 kHz PCM (16/24/32-bit). Resample it first;
  the app will not resample for you.

## The iPad (or phone) can't reach the URL

- **Same network:** the iPad must be on the **same Wi-Fi/LAN** as the computer
  running the app. Guest networks and "client isolation" often block this.
- **Right address:** use one of the LAN addresses the app printed (or the QR code
  in the banner), not `localhost` — `localhost` only works on the computer itself.
- **Firewall:** allow incoming connections on port 8000 on the computer running
  the app. On Windows, approve the prompt the first time; on Linux, open the port
  if a firewall is active.
- **mDNS / `.local`:** if you set the hostname and use a `.local` address and it
  doesn't resolve, use the numeric IP address instead.

## Values are frozen, or the strip shows STALE

- **`STALE · LINK LOST`** means the browser lost its connection to the app.
  Check Wi-Fi; the strip keeps the last values visible but marks them stale so you
  don't trust a frozen number. It reconnects automatically when the network
  returns.
- **`STALE INPUT` / `MIC LOST`** means the app stopped receiving audio (the
  microphone was unplugged or the interface dropped out). Reconnect the same
  microphone; a different one will not silently take over.
- **`AUDIO GAP` / `GAPS n`** means some audio buffers were dropped. Averaging
  windows restart and the gap is recorded; occasional gaps under load are noted,
  not hidden.

## What the calibration badges mean

| Badge | Meaning |
| --- | --- |
| *(none)* + `UNCALIBRATED` | No calibration applied yet; no dB SPL numbers. Spectrum and diagnostics still work in dBFS. |
| `FILE CAL` | A UMIK-1 calibration file is applied automatically (supported UMIK-1 on direct Linux input). |
| `REFERENCE CAL` | An acoustic reference (calibrator or known-SPL source) is applied. |
| `MANUAL CAL` | A manually entered sensitivity (dBFS at 94 dB SPL) is applied. |
| `UNVERIFIED` | A reminder that calibration being *applied* is not the same as being independently verified against a certified meter. It stays on by design. |
| `DEMO` | You're viewing the generated demonstration signal, not a real microphone. |

## The numbers seem too high or too low

- Recheck the calibration mode and value — see the
  [calibration guide](calibration-guide.md).
- On macOS/Windows, the OS input-volume slider changes the digital level and
  invalidates a manual or reference calibration. Set it, note it, and don't
  change it afterwards; recalibrate if you do.
- Readings that go *down* as the show gets louder, or a `Peak since reset` that
  stops rising, mean the input is clipping. Check the `CLIP` indicator and the
  clip-seconds count; a UMIK-1 at its factory 18 dB gain setting clips in the
  low 120s dB SPL. See [headroom and clipping](calibration-guide.md#headroom-and-clipping).
- `Peak since reset` is a **C-weighted** held peak — it is legitimately higher
  than the A-weighted live level and averages. Use its reset arrow to clear it.

## Something else

- The app only serves your local network; it never sends audio or telemetry to
  the internet, so an internet outage doesn't affect it.
- For deeper diagnostics see the [developer reference](developer-reference.md);
  for a dedicated-box install see [deployment](deployment.md).
