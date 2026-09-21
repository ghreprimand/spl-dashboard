# Operator deployment

This is for running SPL Dashboard on a **dedicated, always-on Linux box** at the
microphone — a small appliance you set up once and leave running. If you just
want to run it on your laptop, use `uvx spl-dashboard` from the
[getting-started guide](getting-started.md) instead.

The appliance runs an **installed wheel with the web UI bundled inside it**. It
needs no Node, no compiler and no source checkout at runtime. It can run entirely
offline on an event LAN once installed.

## Prepare the computer

Use a Linux host with a reliable USB port, local storage and a LAN connection.
Install Python 3.11+, `libportaudio2`, `alsa-utils`, `avahi-daemon` (optional, for
`.local` names) and — for automatic UMIK-1 calibration — leave ALSA available.

## Install (online)

The simplest install fetches the release from PyPI into a virtual environment:

```bash
sudo mkdir -p /opt/spl-dashboard
sudo python3 -m venv /opt/spl-dashboard/.venv
sudo /opt/spl-dashboard/.venv/bin/pip install spl-dashboard
```

That installs the `spl-dashboard` command at
`/opt/spl-dashboard/.venv/bin/spl-dashboard`, with the UI already inside it.

To pin a specific version, install `spl-dashboard==0.5.0`.

### Alternative: a local wheel

If you built the wheel yourself (`make wheel` produces
`dist/spl_dashboard-<version>-py3-none-any.whl`), install that file instead:

```bash
sudo /opt/spl-dashboard/.venv/bin/pip install dist/spl_dashboard-0.5.0-py3-none-any.whl
```

## Run as a service

The supplied unit runs the console command as a dedicated user, on port 8000,
with a single worker and a durable data directory. Create the account and enable
startup:

```bash
sudo useradd --system --user-group --groups audio --home-dir /var/lib/spl-dashboard spl
sudo cp deploy/spl-dashboard.service /etc/systemd/system/
sudo cp deploy/spl-dashboard.service.avahi /etc/avahi/services/spl-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now avahi-daemon spl-dashboard
```

The `/opt/spl-dashboard` tree must be readable/executable by `spl`. Systemd
creates `/var/lib/spl-dashboard`, writable by the service user. The service binds
port 8000. Set the computer's hostname to `splbox` if you want
`http://splbox.local:8000/`; Avahi advertises the real hostname, not an invented
alias.

Confirm the installed version and liveness:

```bash
/opt/spl-dashboard/.venv/bin/pip show spl-dashboard        # Version
curl -s http://localhost:8000/api/health                   # schemaVersion, mode, addresses
```

Open the LAN IP on port 8000 if mDNS is unavailable. Use a trusted private event
LAN: the service has same-origin browser-mutation protection but **no user
authentication**, so other trusted LAN participants can control it. Do not
port-forward it. Restrict the bind address in the unit if the host also has an
untrusted interface. Raw event audio and telemetry are never sent anywhere off
the machine.

## Offline / air-gapped install

For a box with no internet during operation, stage everything on a connected
build machine first and copy it across.

On a connected machine with internet, Node and Python:

```bash
# Build the wheel with the UI bundled inside it.
make wheel                    # -> dist/spl_dashboard-<version>-py3-none-any.whl

# Download all runtime dependencies for the target's OS/Python/CPU.
python3 -m pip download --only-binary=:all: --dest wheelhouse \
  dist/spl_dashboard-0.5.0-py3-none-any.whl
```

Build the wheelhouse on the **same OS/Python/CPU architecture** as the appliance
so the binary wheels (numpy, scipy, sounddevice) match. Transfer `dist/`,
`wheelhouse/` and `deploy/` to the appliance (USB/scp), then install offline:

```bash
sudo python3 -m venv /opt/spl-dashboard/.venv
sudo /opt/spl-dashboard/.venv/bin/pip install \
  --no-index --find-links wheelhouse \
  dist/spl_dashboard-0.5.0-py3-none-any.whl
```

`--no-index --find-links wheelhouse` keeps the install offline. Because the UI is
inside the wheel, there is no separate `web/dist` to copy. Archive the wheelhouse
and its hashes for repeatability; unpinned dependency ranges alone do not ensure
reproducible builds. Then set up the service as above.

## Input setup

Select the microphone explicitly in **Input & calibration**. On Linux, devices
with a unique USB serial are bound to that serial and PCM interface, not the
changing card index. Placeholder serials use the physical USB port plus operator
serial confirmation. Other devices use a host/name identity and reject ambiguous
matches. Prefer the serial-bound entry. The app never falls back to the default
microphone.

Use the correct channel and 48 kHz. Confirm the OS input gain and disable any
AGC, suppression or other processing. Then calibrate — see the
[calibration guide](calibration-guide.md). Automatic file calibration is
available for a supported direct UMIK-1 input on Linux; other microphones and
other operating systems use a reference or manual calibration. A service retry
only reopens the selected identity after a disconnect.

## iPad and offline behavior

Open `http://splbox.local:8000/display` (or the LAN IP). Size and place the strip
with its ellipsis control. iPadOS controls window size and placement alongside
Mixing Station. The expanded controls remain scrollable in a shallow window.

A local manifest and home-screen metadata are provided. This release does not
install a service worker or claim an offline-cached PWA shell on plain LAN HTTP.
All assets are served by the appliance; loss of internet has no effect. Loss of
the LAN or appliance makes telemetry unavailable and shows a warning.

## Operation and recovery

- Start a named event for one-second logging. Capture runs even with no event and
  no clients. Event start resets averaging and peak hold.
- Add annotations, reset peak, stop the event, download CSV and event JSON.
- No pause control: stopping an event ends its log; create another to resume.
- Thresholds default to disabled and apply to raw fixed-microphone values.
- A named A-weighted audience offset creates separate estimates. Raw logs remain.
- Input/calibration/threshold changes require stopping the event so its metadata
  cannot silently change mid-log.
- Browser closure does not stop capture or logging. Service restart resumes the
  active event, records a gap, restores the last durable peak and warms new
  windows.
- A disconnect or dropped block restarts averaging windows. Missing intervals are
  flagged rather than synthesized. Peak history keeps a persistent gap warning.
- A disk-write failure produces LOG FAILURE. Stop and resolve storage trouble.

## Upgrade, backup and rollback

The appliance runs an installed wheel, so upgrading means installing a new wheel
into the venv. Plan upgrades between events, never mid-recording. Keep the
previous version's wheel so you can roll back without touching data.

1. **Back up the database first (WAL-safe).** Stop the service, then use SQLite's
   backup API for a consistent standalone copy:

   ```bash
   sudo systemctl stop spl-dashboard
   backup_dir="/var/backups/spl-dashboard-$(date -u +%Y%m%dT%H%M%SZ)"
   sudo mkdir -p "$backup_dir"
   sudo python3 - "$backup_dir/events.sqlite3" <<'PYBACKUP'
   import sqlite3
   import sys
   with sqlite3.connect('/var/lib/spl-dashboard/events.sqlite3') as source:
       with sqlite3.connect(sys.argv[1]) as destination:
           source.backup(destination)
   PYBACKUP
   sudo /opt/spl-dashboard/.venv/bin/pip freeze | sudo tee "$backup_dir/packages.txt" >/dev/null
   ```

   Do not continue if any backup command fails; restart the unchanged service if
   abandoning the upgrade.

2. **Install the new version and restart.**

   ```bash
   sudo systemctl stop spl-dashboard
   sudo /opt/spl-dashboard/.venv/bin/pip install --upgrade spl-dashboard
   # Offline: --no-index --find-links wheelhouse --upgrade dist/spl_dashboard-<version>-py3-none-any.whl
   sudo systemctl start spl-dashboard
   ```

   The UI upgrades with the wheel — there is no separate `web/dist` to replace.

3. **Verify.** Confirm the new version (`pip show spl-dashboard` or
   `/api/health`), check `GET /api/health` reports `schemaVersion` 2 and the
   expected `mode`, and inspect `journalctl -u spl-dashboard -n 100 --no-pager`
   for a clean start with no LOG FAILURE. Open the strip and confirm telemetry.

**Rollback (application only, never the database):** reinstall the previous
version and restart. **Do not** delete or overwrite `events.sqlite3` —
accumulated events must survive a rollback. The `audience_mappings` table is
additive; additive SQL changes do **not** guarantee backward compatibility, since
older Pydantic models reject unknown configuration fields. Before rolling back to
an older version, validate the current configuration against that version using an
isolated copy of the database — never the live data directory. Roll back only to a
verified compatible version.

```bash
sudo systemctl stop spl-dashboard
sudo /opt/spl-dashboard/.venv/bin/pip install --force-reinstall "spl-dashboard==<previous>"
sudo systemctl start spl-dashboard
```

## Storage and maintenance

`events.sqlite3` (in the data directory) holds configuration, event metadata, full
telemetry snapshots, annotations and the durable `audience_mappings` library.
One-second records include raw and estimated values, calibration hash, health,
warm-up and alarm flags. The `summary.json` export is event **metadata only**;
the CSV export carries the raw metric set (LAS/LAeq1/LAeq10/LCpeak/LASmax) plus
estimated LAS/LAeq1/LAeq10 (no estimated-LASmax column). There is no bulk
mapping-library export API — the SQLite file is the backup unit.

Retention is indefinite. Monitor free space and archive events; there is no
automatic deletion. Stop the service before copying the SQLite file, or use
SQLite's online backup API so WAL data is included. Raw audio is never recorded.
Local synthetic WAV fixtures go in the data directory's `fixtures/`.

```bash
sudo systemctl status spl-dashboard --no-pager
sudo journalctl -u spl-dashboard -n 100 --no-pager
```

Run only one worker and one process per data directory; the process lock rejects a
second instance. Service restart is rate-limited. Validate a cold boot and loss of
external internet before the first event.

Audience reading location is shared across all clients. Apply a mapping from one
browser and connected strips follow. Changing only the reading location does not
restart capture or interrupt logging. See
[microphone placement and venue correction](microphone-placement.md) for the
mapping workflow.
