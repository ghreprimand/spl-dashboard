# SPL Dashboard documentation

Start with the [project README](../README.md) for what the app is and how to
install it. This index organises the rest by who you are.

## For users

You run the app on the microphone computer and read it on an iPad or browser.

- [Getting started](getting-started.md) — install to first reading, step by step.
- [Calibration guide](calibration-guide.md) — which mode for which microphone.
- [Tablet setup](tablet-setup.md) — home-screen app and window overlap on iPad or Android.
- [Microphone placement and venue correction](microphone-placement.md) — where to
  put the mic and how audience estimates work.
- [Troubleshooting](troubleshooting.md) — common problems and fixes.

## For operators

You run it on a dedicated always-on computer, or manage upgrades and backups.

- [Deployment](deployment.md) — install from PyPI or a local wheel, run it as a
  service on a dedicated Linux box, and the offline install path.
- Upgrade, backup and rollback — in [deployment](deployment.md).
- [Hardware acceptance procedure](hardware-acceptance.md) — the bench checks and
  the current verification status.
- [Releasing](releasing.md) — how new versions are built and published (for
  maintainers).

## For developers

You want to change the code, the DSP or the calibration.

- [Developer reference](developer-reference.md) — source map, state ownership,
  configuration contract and development workflow.
- [Architecture](architecture.md) — data flow, stack, network API and schema.
- [DSP requirements](dsp-and-calibration.md) and
  [DSP implementation, sources and tolerances](dsp-implementation.md).
- [Spectrum analyzer definition and validation](spectrum-analyzer.md).
- [UMIK sensitivity conventions](umik-sensitivity.md).
- [Product brief](product-brief.md) and [research notes](research.md).
- [Current handoff](HANDOFF.md) — present state and evidence.
- Architecture decision records: [`decisions/`](decisions/).

## Screenshots

Regenerate the documentation screenshots with `make screenshots` (builds the UI,
runs the demo source and captures a headless browser). They live in
[`screenshots/`](screenshots/).
