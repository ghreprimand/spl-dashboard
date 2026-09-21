# Appliance deployment

## Prepare the test computer

Use a Linux host with a reliable USB port, local storage and an event LAN
connection. No internet is needed while operating. Initial installation needs
packages downloaded ahead of time or internet access during provisioning.

For Debian/Ubuntu, install Python 3.11+, Python venv support, `libportaudio2`,
`alsa-utils`, `avahi-daemon` and `rsync`. The appliance runs an **installed wheel**, not an editable
checkout, and needs no internet, Node or compiler at runtime.

### Build the release on a connected build machine

Do this where you have internet and Node (a workstation, not the offline
appliance). Build the backend wheel, the static UI, and a wheelhouse of all
runtime dependencies so the appliance can install fully offline:

```bash
# Run in a build venv; output goes explicitly to dist/.
python3 -m pip wheel --no-deps --wheel-dir dist ./server

# Use a Python/OS/architecture matching the target appliance.
# Select the exact release wheel if dist contains more than one version.
python3 -m pip download --only-binary=:all: --dest wheelhouse \
  dist/spl_dashboard-0.5.0-py3-none-any.whl

# Static UI -> web/dist
cd web && npm ci && npm run build && cd ..
```

Transfer `dist/`, `wheelhouse/`, `deploy/` and `web/dist/` to the appliance (USB/scp).
Build the wheelhouse on the same OS/Python/CPU architecture as the appliance so
binary wheels (numpy, scipy, sounddevice) match.

### Install on the appliance (offline)

Lay out `/opt/spl-dashboard` for the supplied service unit — it expects the venv
at `/opt/spl-dashboard/server/.venv` and the UI at `/opt/spl-dashboard/web/dist`:

```bash
sudo mkdir -p /opt/spl-dashboard/server /opt/spl-dashboard/web
sudo python3 -m venv /opt/spl-dashboard/server/.venv
sudo /opt/spl-dashboard/server/.venv/bin/pip install \
  --no-index --find-links wheelhouse \
  dist/spl_dashboard-0.5.0-py3-none-any.whl
sudo mkdir -p /opt/spl-dashboard/web/dist
sudo cp -a web/dist/. /opt/spl-dashboard/web/dist/
```

`--no-index --find-links wheelhouse` keeps the install offline. Archive the actual wheelhouse and hashes for repeatability;
unpinned dependency ranges alone do not ensure reproducible builds.
No source checkout is required at runtime; only the venv and `web/dist` matter.

The following commands create the service account and enable automatic startup.
Run them on the intended appliance after the application is installed. If the
account already exists, skip `useradd` and ensure it belongs to the audio group.

```bash
sudo useradd --system --user-group --groups audio --home-dir /var/lib/spl-dashboard spl
sudo cp deploy/spl-dashboard.service /etc/systemd/system/
sudo cp deploy/spl-dashboard.service.avahi /etc/avahi/services/spl-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now avahi-daemon spl-dashboard
```

The `/opt/spl-dashboard` tree (venv and `web/dist`) must be readable/executable
by `spl`. Systemd creates `/var/lib/spl-dashboard`, writable by the service user.
No write permission to the application tree is needed. The service binds port
8000. Set the computer hostname to `splbox` if you want
`http://splbox.local:8000/`; Avahi advertises the existing hostname, not an
invented alias.

Confirm the installed version after starting: `pip show spl-dashboard`
in the appliance venv, or `curl -s http://localhost:8000/openapi.json` and read
`.info.version`. `GET /api/health` returns `schemaVersion` (currently 2),
`mode` and input flags for a quick liveness check.

Open the appliance LAN IP on port 8000 if mDNS is unavailable. Use a trusted
private event LAN. The service has same-origin browser mutation protection but
no user authentication; other trusted LAN participants can control it. Do not
port-forward it. Restrict the bind address in the unit if the host also has an
untrusted interface. Raw event audio and telemetry are never sent to the cloud.

## Input setup

Select the UMIK explicitly in **Input & calibration**. Linux devices with a unique USB
serial are bound to that serial and PCM interface, not the changing card index.
Placeholder serials use the physical USB port plus operator serial confirmation.
Other devices use a host/name identity and reject ambiguous matches. Prefer the
serial-bound entry. The app never falls back to the default microphone.

Use the correct channel and 48 kHz. Confirm the OS input gain and disable any
AGC, suppression or other processing. Import the serial/orientation-specific
file. Automatic file calibration is available for the supported direct UMIK-1
input. Confirm the physical serial for units with placeholder USB serials.
Follow the hardware acceptance procedure for independent accuracy validation;
a separate reference is optional. A service retry only reopens the selected
identity after a disconnect.

## iPad and offline behavior

Open `http://splbox.local:8000/display`. Size and place the strip inside the
window using its ellipsis control. iPadOS controls window size and positioning
alongside Mixing Station; test the actual attainable dimensions and touch
behavior. The expanded controls remain scrollable in a shallow window.

A local manifest and home-screen metadata are provided. This release does not
install a service worker or claim an offline-cached PWA shell on plain LAN HTTP.
All assets are served by the appliance; WAN loss has no effect. Loss of the LAN
or appliance makes telemetry unavailable and must show a warning.

## Operation and recovery

- Start a named event for one-second logging. Capture runs even with no event
  and no clients. Event start resets averaging and peak hold.
- Add annotations, reset peak, stop the event, download CSV and event JSON.
- No pause control: stopping an event ends its log; create another event to resume.
- Thresholds default to disabled and apply to raw fixed-microphone values.
- A named A-weighted audience offset creates separate estimates. Raw logs remain.
- Input/calibration/threshold changes require stopping the event so its metadata
  cannot silently change mid-log.
- Browser closure does not stop capture or logging. Service restart resumes the
  active event, records a gap, restores the last durable peak and warms new windows.
- A disconnect or dropped block restarts averaging windows. Missing intervals
  are flagged rather than synthesized. Peak history has a persistent gap warning.
- A disk-write failure produces LOG FAILURE. Stop and resolve storage trouble.

## Upgrade, backup and rollback

The appliance runs an installed wheel, so **copying `server/src` alone does not
change the running backend** — you must install a new wheel into the venv. Plan
upgrades between events, never mid-recording. Keep the previous wheel and the
previous `web/dist` so you can roll the application back without touching data.

1. **Stage the new release offline.** Build the wheel, `web/dist` and dependency
   wheelhouse on a connected build machine (see "Build the release" above) and
   transfer them to the appliance before you stop the service.
2. **Back up the database first (WAL-safe).** Stop the service, then use SQLite's
   backup API to include any residual WAL in a consistent standalone backup. Run
   these commands on the appliance from the directory containing the staged release:

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
   sudo cp -a /opt/spl-dashboard/web/dist "$backup_dir/web-dist"
   sudo /opt/spl-dashboard/server/.venv/bin/pip freeze | sudo tee "$backup_dir/packages.txt" >/dev/null
   ```

   Keep the old application wheel and dependency wheelhouse alongside this backup.
   Do not continue installation if any backup command fails. Restart the unchanged
   service if abandoning the upgrade. An online SQLite backup can also be used,
   but never copy only a live main database file and assume WAL was included.

3. **Install the new wheel and UI, then restart.**

   ```bash
   sudo systemctl stop spl-dashboard
   sudo /opt/spl-dashboard/server/.venv/bin/pip install \
     --no-index --find-links wheelhouse --upgrade \
     dist/spl_dashboard-0.5.0-py3-none-any.whl
   sudo rsync -a --delete web/dist/ /opt/spl-dashboard/web/dist/
   sudo systemctl start spl-dashboard
   ```

   For a UI-only change you can replace `web/dist` and restart without a new
   wheel; for any backend change the wheel install is mandatory.
4. **Verify.** Confirm the new version (`pip show spl-dashboard` or
   `/openapi.json` `.info.version`), check `GET /api/health` reports `schemaVersion`
   2 and the expected `mode`, and inspect `journalctl -u spl-dashboard -n 100 --no-pager` for a clean
   start with no LOG FAILURE. Open the strip and confirm live telemetry.

**Rollback (application only, never the database):** reinstall the previous wheel
and restore the previous `web/dist`, then restart. **Do not** delete or overwrite
`events.sqlite3` — accumulated events must survive a rollback. The `audience_mappings` table is additive; `lasMaxDb` is a field inside frame JSON,
not a database column. Additive SQL changes do **not** guarantee backward
compatibility: older Pydantic models reject unknown configuration fields such as
`audienceDisplay`. Before rollback, validate the current configuration against the
target version using an isolated copy of the database. Do not point the test at the
live data directory. Roll back only to a verified compatible version; otherwise
prepare a reviewed configuration migration that preserves event/frame records.
There is no automatic downgrade migration. The commands below assume compatibility
has been verified and the matching previous wheel/UI have been staged.

Set `previous_wheel` to the exact verified prior wheel path before running:

```bash
sudo systemctl stop spl-dashboard
sudo /opt/spl-dashboard/server/.venv/bin/pip install \
  --no-index --find-links wheelhouse --force-reinstall \
  "$previous_wheel"
sudo rsync -a --delete web/dist.previous/ /opt/spl-dashboard/web/dist/
sudo systemctl start spl-dashboard
```

Current baseline: 0.4.4 is installed on the NUC and its automated suite passes
(100 server + 18 web tests). That is a software/bench baseline only — treat the
independent hardware acceptance in `hardware-acceptance.md` as the gate before
relying on absolute values, and record which release was used for each event.

## Storage and maintenance

`events.sqlite3` holds configuration, event metadata, full telemetry snapshots,
annotations and the durable `audience_mappings` library. One-second records
include raw and estimated values, calibration hash, health, warm-up and alarm
flags. The `summary.json` export is event **metadata only** (event row, stored
configuration including original calibration text and notes, annotations and a
frame count) — not per-frame telemetry. Exported CSV carries the full raw metric
set (LAS/LAeq1/LAeq10/LCpeak/LASmax) plus estimated LAS/LAeq1/LAeq10; it has no
estimated-LASmax column. There is no bulk mapping-library export API — the
SQLite file is the backup unit.

Retention is indefinite in this release. Monitor free space and archive events;
there is no automatic deletion. Stop the service before copying the SQLite file,
or use SQLite's online backup API so WAL data is included. Raw audio is never
recorded. Local synthetic WAV fixtures go in the data directory's `fixtures/`.

```bash
sudo systemctl status spl-dashboard --no-pager
sudo journalctl -u spl-dashboard -n 100 --no-pager
```

Configure journald retention on the host. Run only one Uvicorn worker and only
one process per data directory. The process lock rejects a second instance.
Service restart is rate-limited. Validate a cold boot and loss of external
internet before the first event; a UPS is optional after hardware testing.

Audience reading location is shared across all clients. Apply mapping from a
workstation and connected iPad strips follow automatically after their initial
upgrade reload. Mapping identity and date/time appear in controls and the strip.
Changing only reading location does not restart capture or interrupt logging.

Use **Saved audience mappings** to select a previously captured profile and
**Use selected mapping on all displays** to activate it. Stop recording first.
Sort by name, date or correction. Deletion removes an inactive library entry after
confirmation; previous event records remain. Use **Clear loaded mapping** to return every display to measured levels while
retaining the saved profile. You can then select and delete that entry. Stop
recording before clearing; averages restart. Reuse requires unchanged venue/speaker/mic placement.
