# SPL Dashboard

SPL Dashboard is a sound-pressure-level (SPL) monitor for live events. You run it
on the computer that has your measurement microphone plugged in; it does all the
audio capture, calibration and metering there and serves a live dashboard on your
local network. An iPad, phone or laptop on the same Wi-Fi opens the dashboard in a
web browser — those devices only ever receive numbers, never audio.

![The strip display](docs/screenshots/strip.png)

## How it fits together

```text
   ┌─────────────┐      USB      ┌────────────────────────────┐
   │ Measurement │ ────────────▶ │  Computer running          │
   │ microphone  │               │  SPL Dashboard             │
   └─────────────┘               │  (capture · DSP · logging) │
                                 └──────────────┬─────────────┘
                                                │ your Wi-Fi / LAN
                        ┌───────────────────────┼───────────────────────┐
                        ▼                       ▼                        ▼
                     iPad browser          phone browser           laptop browser
                     (views /display)      (views dashboard)       (admin console)
```

**This does not install on an iPad.** The iPad (or phone, or other laptop) only
*views* the dashboard in its web browser. The one and only thing you install is
`spl-dashboard`, on the computer with the microphone.

## Which setup is for me?

| Your situation | What to do |
| --- | --- |
| **Laptop only** — you mix and monitor on the same machine | Install and run `spl-dashboard`; open `http://localhost:8000/display` on the same laptop. |
| **Laptop + iPad** — you want a big readout at front of house | Run `spl-dashboard` on the laptop; open the LAN `/display` URL it prints on the iPad's browser. |
| **Dedicated box (recommended)** — a small always-on Linux computer or Raspberry Pi at the mic | Install it as a service on that box; see [operator deployment](docs/deployment.md). |

## Platform support — read this first

| Platform | Runs? | UMIK-1 calibration | Other mics |
| --- | --- | --- | --- |
| **Linux** (x86 or Raspberry Pi) | Yes, **recommended** | Automatic: load the miniDSP cal file and you're done | Calibrator or typed-in sensitivity |
| macOS | Yes | Frequency response from the file, but the **level must be set by you** (calibrator or typed-in sensitivity) | Same |
| Windows | Yes | Same as macOS | Same |

Why the difference: the level number in a UMIK-1 cal file is only valid once
the operating system's own input-gain stage is known. On Linux the app can
verify there isn't one. On macOS and Windows it doesn't yet read the OS input
slider, so it refuses to guess. Reading that slider is planned; until then,
Mac/Windows users need a calibrator or a known sensitivity (see the
[calibration guide](docs/calibration-guide.md)). See the [roadmap](ROADMAP.md).

**Recommended setup:** a small always-on Linux box with the mic plugged in
(an old laptop, a mini PC, or a Raspberry Pi 4/5 on 64-bit Raspberry Pi OS)
sitting at the mic position, and the iPad as the display. It should run fine
on a Pi 4 or 5 — that has not been tested by the project yet; reports welcome.

## Install and run

First install [uv](https://docs.astral.sh/uv/) (a single small tool), then run the
dashboard with `uvx`.

**Linux** — install the PortAudio runtime first (once):

```bash
sudo apt install libportaudio2        # Debian/Ubuntu; other distros: your equivalent
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx spl-dashboard
```

**macOS:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx spl-dashboard
```

**Windows** (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uvx spl-dashboard
```

macOS and Windows get PortAudio automatically from the `sounddevice` package;
only Linux needs `libportaudio2` installed separately.

When it starts, it prints the address to open on this computer and the addresses
to open on other devices on your network. New here? Follow the
**[getting-started walk-through](docs/getting-started.md)**.

### On an iPad, next to Mixing Station

Open the strip address in Safari and use **Share → Add to Home Screen**; the
icon opens the strip as a menuless full-screen app. Launch it, open Mixing
Station on top, and resize Mixing Station so it leaves enough room at the top of
the screen to see the strip above it. Details, plus Android notes, in the
[tablet setup guide](docs/tablet-setup.md).

### Upgrade

```bash
uvx spl-dashboard@latest        # run the newest release
```

## What you'll see

| | |
| --- | --- |
| ![Spectrum analyzer](docs/screenshots/spectrum.png) | ![Input & calibration](docs/screenshots/input-calibration.png) |
| The spectrum analyzer | Input & calibration |
| ![Event log](docs/screenshots/event-log.png) | ![First-run banner](docs/screenshots/first-run.png) |
| The event log | The getting-started banner |

## Documentation

- **[Documentation index](docs/README.md)** — everything, organised by audience.
- [Roadmap](ROADMAP.md) — what's planned and what isn't.
- [Getting started](docs/getting-started.md) · [Calibration guide](docs/calibration-guide.md) · [Tablet setup](docs/tablet-setup.md) · [Troubleshooting](docs/troubleshooting.md)

## Important: what this is, and is not

> SPL Dashboard is an operational monitor, not a compliance meter. It makes no
> IEC 61672, Class 1/2, regulatory or legal claim. Absolute levels have been
> compared against REW on the same microphone with matching results, but have
> not been independently verified against a certified sound level meter. Use
> your own judgement and your own reference for anything that matters.

## License

Copyright (C) 2026 ghreprimand.

SPL Dashboard is licensed under **GPL-3.0-only** (GNU General Public License,
version 3 only). See [LICENSE](LICENSE) for the full terms. This program is
distributed without any warranty; see the license for details. Third-party
dependencies retain their respective licenses.
