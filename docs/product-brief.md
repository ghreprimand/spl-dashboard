# Product brief

## Problem

A live-sound operator mixes from a 13-inch iPad using Mixing Station while the Behringer WING
Rack stays on stage. There is no permanent front-of-house workstation, yet
show volume is frequently questioned. Console meters describe electrical
signal, not acoustic level in the room. The operator needs continuous, defensible,
easy-to-read acoustic information without giving up most of the iPad screen.

## Product statement

Build a headless, LAN-only SPL telemetry appliance. A calibrated UMIK-1 connects
to a small Linux computer placed near a fixed audience measurement microphone.
The appliance calculates and logs acoustic metrics, then serves a responsive
web dashboard over the event router. On the iPad, the dashboard runs as a small
PWA/Stage Manager window beside or above Mixing Station.

## Primary strip

Left to right:

1. `LAS`: immediate A-weighted Slow level.
2. `LAeq1`: rolling one-minute A-weighted energy average.
3. `LAeq10`: rolling ten-minute A-weighted energy average.
4. `LCpeak`: highest C-weighted peak since event/reset.
5. Compact 1/3-octave spectrum without tiny axis labels.
6. Connection/calibration/clipping state.

The strip must remain legible in a window roughly one inch high on a 13-inch
iPad. Colour communicates urgency but text/icons must carry the same meaning.

## Expanded dashboard

- SPL history and threshold crossings.
- Larger 1/3-octave RTA and optional spectrogram.
- Raw fixed-microphone values and separately labelled audience estimates.
- Venue/profile selector.
- Event start, pause, reset-peak, annotation, stop, and export controls.
- Calibration file, field-trim, input level, clipping, sample rate, uptime, and
  last-frame health.
- Downloadable CSV and a concise event summary.

## Operational workflow

1. Mount the UMIK in a repeatable safe position.
2. Connect it to the appliance and confirm the serial/calibration file.
3. Select or create a venue profile.
4. Start a named event; logging begins on the appliance.
5. Open `http://splbox.local:8000/` on the iPad.
6. Monitor while mixing; use annotations when a complaint or notable event
   occurs.
7. Stop and export after the show.

## Success criteria

- Cold boot to live strip without keyboard or monitor.
- No internet dependency.
- Dashboard reconnects after Wi-Fi or iPad sleep without stopping the log.
- One-second records survive browser closure and service restart.
- Clear alarms for stale data, clipping, missing calibration, and mic removal.
- A venue profile never overwrites or hides the raw measured record.
- Correct calculations demonstrated with automated reference-signal tests and
  comparison against established measurement software/hardware.

## Non-goals for the first release

- Controlling WING or Mixing Station.
- Transfer-function, phase, or system-alignment measurements.
- Automatic system EQ.
- Streaming or recording event audio.
- Regulatory compliance certification.
- Predicting room SPL from specifications alone.
