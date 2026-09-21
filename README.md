# SPL Dashboard

An offline, LAN-served sound monitor for an iPad beside Mixing Station. The Linux
appliance owns capture, DSP and event logging. Browsers receive low-rate numbers,
never audio. The strip is the primary interface, with size and placement saved
independently in each browser.

**Hardware-test release:** generated signals, WAV replay, USB capture plumbing,
file-based UMIK-1 calibration, DSP, logging and the configurable display are
implemented. A supported direct ALSA UMIK-1 input uses the supplied sensitivity
file to produce SPL values. **FILE CAL** means that calibration is applied; an
independent physical accuracy comparison is still pending. See
[UMIK sensitivity conventions](docs/umik-sensitivity.md).

## Develop

Python 3.11+; a Node version supported by the locked Vite release. Linux USB
capture also needs the system PortAudio library (`libportaudio2` on Debian/Ubuntu).
Demo and WAV modes work without that library.

```bash
make server-install
make web-install
make dev-server
# Another terminal:
make dev-web
```

Open `http://localhost:5173/` for setup, or `/display` for the strip. The initial
source is a clearly labelled generated demonstration. Vite proxies the service
on port 8000. All measurement calculations happen in the service.

```bash
make check
# Serve the compiled UI and service together:
./scripts/run-appliance.sh
```

Production UI: `http://localhost:8000/`. Run a single Uvicorn worker; one process
owns each data directory and a second instance is rejected by a file lock. This
is a plain LAN HTTP appliance and ships **no browser service worker** (only a
home-screen manifest). `SPL_DATA_DIR` selects durable storage (default
`~/.local/share/spl-dashboard`). Events, configuration and the audience-mapping
library live in `events.sqlite3`; raw audio is never stored.

## Set up the strip

Under **Your display**, adjust width, height, digit size, spacing and position.
The compact preset is a starting point. Open **Strip display** and use its
ellipsis button to reopen controls. Width is capped to the window and smaller
windows reduce detail. Settings persist on that browser. iPadOS window controls
place Safari/the home-screen window beside Mixing Station.

## Test without hardware

Generate a local reference file inside the appliance data directory:

```bash
python3 scripts/generate-reference.py ~/.local/share/spl-dashboard/fixtures/reference.wav
```

Select **Local WAV replay**, enter `reference.wav`, then apply. Expect raw RMS
near -23.0103 dBFS and peak near -20 dBFS. Replay stops at EOF; it never silently
loops. Acoustic metrics remain unavailable until an explicit reference is set.
For synthetic comparison only, assigning that signal a 94 dB reference should
produce about 94 dB LAS/Leq after settling and 97.01 dB C peak after resetting
peak. This establishes software scaling, not microphone calibration.

## Audience mapping

An optional A-weighted venue offset lets the strip show an estimated audience
level in place of the fixed-microphone A readings in the strip. Capture a mapping from the guided
card (fixed position, three audience positions, return check), then apply it.
Applied mappings persist in a durable SQLite library with name, correction and
capture note; save/apply, activate, sort and confirmed-delete are available.
**Clear loaded mapping** returns every display to measured levels without
deleting the saved profile. The chosen reading location (measured vs. estimated)
is shared across all clients through telemetry. Applying, activating or clearing
a mapping restarts averaging windows and is blocked while an event is recording;
toggling only the reading location does neither. Raw logs, C peak, spectrum and
thresholds always stay fixed-microphone data. See
[microphone placement and venue correction](docs/microphone-placement.md) and
ADRs [0005](docs/decisions/0005-audience-mapping.md),
[0008](docs/decisions/0008-shared-reading-location.md) and
[0009](docs/decisions/0009-audience-mapping-library.md).

## Documents

Start with [the current handoff](docs/HANDOFF.md), then the
[developer reference](docs/developer-reference.md) for source ownership, settings,
state boundaries and troubleshooting. Historical ADRs explain decisions, not
always current behavior; current guides take precedence.

- [Product brief](docs/product-brief.md) and [architecture](docs/architecture.md)
- [DSP requirements](docs/dsp-and-calibration.md) and [implementation, sources and tolerances](docs/dsp-implementation.md)
- [Spectrum analyzer definition and validation](docs/spectrum-analyzer.md)
- [UMIK sensitivity conventions](docs/umik-sensitivity.md)
- [Microphone placement and venue correction](docs/microphone-placement.md)
- [Appliance deployment](docs/deployment.md)
- [Hardware acceptance procedure](docs/hardware-acceptance.md)
- [Current handoff](docs/HANDOFF.md)

This is an operational monitor, with no IEC, Class 1/Class 2, regulatory or legal
compliance claim. Fixed-microphone values and audience estimates remain distinct.

## License

Copyright (C) 2026 ghreprimand.

SPL Dashboard is licensed under **GPL-3.0-only** (GNU General Public License,
version 3 only). See [LICENSE](LICENSE) for the full terms.

This program is distributed without any warranty; see the license for details.
Third-party dependencies retain their respective licenses. If distributing
compiled bundles or a wheelhouse, retain their required license and notice files.
