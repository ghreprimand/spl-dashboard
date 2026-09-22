# Changelog

All notable changes to SPL Dashboard are recorded here. This project adheres to
[Semantic Versioning](https://semver.org/).

## Unreleased

### Documentation

- Added microphone headroom guidance: the UMIK-1's factory 18 dB gain setting
  clips around the low 120s dB SPL, the 0 dB setting raises the limit to the
  capsule's 133 dB rating, what the clip indicator can and cannot see, and
  higher-headroom XLR alternatives. README, calibration guide, troubleshooting.

## 0.5.1

### Fixed

- **Windows:** the single-instance lock imported `fcntl`, which does not exist on
  Windows, so `uvx spl-dashboard` failed to start there. The lock now uses
  `msvcrt` on Windows and `fcntl` elsewhere.
- **Strip:** "Maximum live level" is now "Max live level" so the label and its
  reset button no longer wrap at typical strip widths.

### Documentation

- New [tablet setup guide](docs/tablet-setup.md): making the strip a menuless
  home-screen app, the window-overlap workflow next to a mixer app on iPad, and
  best-effort notes for Android (HTTPS requirement for standalone shortcuts,
  split screen and pop-up windows).
- Corrected the manual-sensitivity guidance: the value is the raw dBFS at
  94 dB SPL in this app's scale, **not** the miniDSP Sens Factor (for a UMIK-1
  on direct input it is Sens Factor − 30 dB).
- Release workflow now creates a GitHub Release with the changelog entry and the
  built wheel/sdist attached; the TestPyPI rehearsal job was removed.

## 0.5.0

First public PyPI release. The distribution is renamed and packaged so a
non-technical audio tech can install and run it with `uvx spl-dashboard` on
Linux, macOS or Windows, and view the dashboard from an iPad or any LAN browser.

### Packaging

- Renamed the distribution from `spl-dashboard-server` to **`spl-dashboard`**
  (the import package stays `spl_dashboard`).
- The built web UI is now **bundled inside the wheel** (`spl_dashboard/static/`),
  so no separate `web/dist` is needed at runtime. `make wheel` produces a
  self-contained wheel; `make ui-bundle` builds and copies the UI.
- Added PyPI metadata: description, README long description, project URLs,
  classifiers (OS Independent, Python 3.11+, Multimedia :: Sound/Audio ::
  Analysis) and keywords.
- `SPL_WEB_DIST` is now a true developer override; the bundled UI is the default.

### Running

- Added the **`spl-dashboard`** console command: starts Uvicorn with one worker
  on `0.0.0.0:8000`, honours `--host`/`--port`/`--data-dir`, and defaults the
  data directory to a per-user platform location (via `platformdirs`).
- On start it prints the local URL and every LAN `/display` URL, plus a reminder
  that other devices only view the dashboard. Also exposed at `GET /api/addresses`
  and included in `GET /api/health`.
- Added a dismissible first-run banner in the admin console with the LAN
  `/display` URL(s) and a QR code; it stays until a calibration is applied.
- Added the operational-monitor disclaimer to the admin footer and the banner.

### Calibration

- **Guided reference capture:** `POST /api/reference/capture` averages a few
  seconds of raw RMS dBFS to fill the reference value; a "Capture raw RMS now"
  button was added to the UI.
- **Manual sensitivity mode:** a new `manual` calibration mode with a single
  "dBFS at 94 dB SPL" field, a mandatory interface/OS-gain note, and a distinct
  `MANUAL CAL` badge.
- **Broader calibration-file import:** added coverage and fixtures for miniDSP
  UMIK-2, Dayton iMM-6/EMM-6/UMM-6, REW `.cal` and Earthworks-style two-column
  files. A sensitivity is only reported when the file contains one; it is never
  guessed.

### Documentation

- Rewrote the README front page for a non-technical audience (topology diagram,
  "which setup is for me?", per-OS install, screenshots, disclaimer).
- Added a getting-started walk-through, a calibration guide, a troubleshooting
  guide and an audience-organised documentation index.
- Rewrote deployment around installing from PyPI or a local wheel, keeping the
  offline/air-gapped path as a subsection.
- Updated the handoff and hardware-acceptance docs to state the verification
  status accurately: levels were compared against REW on the same microphone with
  matching results, but have **not** been independently verified against a
  certified sound level meter, and there is no plan to pursue that. This remains
  an operational monitor with no IEC 61672 / Class 1/2 / regulatory claim.
- Added generated documentation screenshots and a `make screenshots` target.

### CI and release

- CI runs `make check` on Linux across Python 3.11 and 3.12, and the Python tests
  on macOS and Windows.
- Added a tag-triggered release workflow that builds the UI-bundled wheel and
  sdist and publishes to TestPyPI then PyPI using Trusted Publishing (OIDC).
