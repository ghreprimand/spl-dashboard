# SPL Dashboard

An offline, LAN-served sound-pressure-level (SPL) monitor for live events. You run
it on the computer that has the measurement microphone attached; it does all audio
capture, calibration and DSP locally and serves a web dashboard on your local
network. An iPad, phone or laptop browser on the same Wi-Fi views the readings —
browsers only ever receive numbers, never audio.

## Install and run

Install [uv](https://docs.astral.sh/uv/), then:

```bash
uvx spl-dashboard
```

On start it prints the local URL and the LAN URLs to open on other devices.

**Linux only:** install the PortAudio runtime first (`sudo apt install libportaudio2`
on Debian/Ubuntu). macOS and Windows get PortAudio from the `sounddevice` wheel.

## What it is (and is not)

SPL Dashboard is an operational monitor, not a compliance meter. It makes no
IEC 61672, Class 1/2, regulatory or legal claim. Absolute levels have been
compared against REW on the same microphone with matching results, but have not
been independently verified against a certified sound level meter. Use your own
judgement and your own reference for anything that matters.

## Documentation

Full documentation, screenshots, the getting-started walk-through, the calibration
guide and the troubleshooting guide live in the project repository:

- Homepage and source: https://github.com/ghreprimand/spl-dashboard

## License

Copyright (C) 2026 ghreprimand. Licensed under **GPL-3.0-only**. See `LICENSE`.
