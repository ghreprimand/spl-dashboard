# Getting started

This is the full walk-through, from nothing installed to a live reading on an
iPad beside Mixing Station. It should take about fifteen minutes the first time.

You only install software on **one** computer: the one with the microphone. The
iPad and any other devices just open a web page.

## 1. Install uv

[uv](https://docs.astral.sh/uv/) is a small tool that fetches and runs Python
applications. Install it once:

- **Linux / macOS:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows (PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

Close and reopen your terminal afterwards so `uv` is on your path.

## 2. Linux only: install PortAudio

On Linux the audio library is separate. On Debian/Ubuntu:

```bash
sudo apt install libportaudio2
```

On macOS and Windows you can skip this — it comes with the app.

## 3. Start the dashboard

Plug in your microphone, then run:

```bash
uvx spl-dashboard
```

The first run downloads the app; later runs are instant. It prints something like:

```text
  On this computer:
    Admin console:  http://localhost:8000/
    Strip display:  http://localhost:8000/display

  From an iPad, phone or laptop on the same Wi-Fi (open /display):
    http://192.168.1.50:8000/display
```

Open the **admin console** (`http://localhost:8000/`) in a browser on this
computer. You'll see a getting-started banner with those same addresses and a QR
code you can scan from the iPad.

## 4. Choose your input

In **Input & calibration**:

1. Set **Input source** to **USB microphone**.
2. Pick your microphone under **Microphone**. On Linux, prefer the entry marked
   *USB serial* if there is one — it stays bound to that exact microphone.
3. Leave the input at 48 kHz and choose the correct channel.
4. In your operating system's sound settings, turn **off** any automatic gain
   control, noise suppression or "voice" processing for this input, and set a
   fixed input level.

Until you calibrate, you'll see raw levels (dBFS), the spectrum and input health,
but no dB SPL numbers. That's expected.

## 5. Calibrate

Pick the mode that matches your gear — the
[calibration guide](calibration-guide.md) has a short "which setup is for me?"
section. In brief:

- **UMIK-1 on Linux:** load its calibration file; you'll see `FILE CAL`.
- **UMIK-1/UMIK-2 elsewhere, or any mic with a calibrator:** load the frequency
  file (if you have one), then set the level with **Known-level acoustic
  reference** — fit the calibrator, click **Capture raw RMS now**, enter the
  calibrator's level, add a note, and apply. You'll see `REFERENCE CAL`.
- **You only know the sensitivity figure:** use **Manual sensitivity** and enter
  the dBFS at 94 dB SPL. You'll see `MANUAL CAL`.

Once a calibration is applied, the SPL numbers appear on the strip.

## 6. Open the strip on the iPad

On the iPad, open the `/display` address the app printed (or scan the QR code in
the banner). This is the **strip** — the primary readout.

- Tap the **•••** button on the strip to open display settings.
- Adjust width, height, digit size, spacing and position so it reads well at the
  size you'll actually use. These settings are saved in that browser.
- To make it a menuless home-screen app and keep it visible next to your mixer
  app, see [Putting the strip on an iPad or Android tablet](tablet-setup.md).

## 7. Log an event (optional)

In the admin console's **Event log**, give the event a name and press **Start
event**. From then on the app records one reading per second, which you can
export as CSV or JSON afterwards. Closing the browser does not stop logging — the
computer with the microphone keeps measuring.

## Next steps

- [Calibration guide](calibration-guide.md) — get the numbers right.
- [Microphone placement and venue correction](microphone-placement.md).
- [Troubleshooting](troubleshooting.md) — if something doesn't look right.
