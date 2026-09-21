# ADR 0002: Shared measurement runtime and explicit reference validation

- Status: accepted
- Date: 2026-09-20

## Decision

Replace per-WebSocket mock generation with one service-owned input/DSP loop,
independent of browsers. A bounded callback queue contains temporary audio;
only low-rate telemetry reaches clients and SQLite. One worker is enforced by
a data-directory lock. A single active event has a configuration snapshot.
Settings changes are blocked during events. SQLite WAL and FULL synchronous
writes persist one-second snapshots; restart retains the event, records a gap,
restores peak from the last durable frame and restarts averaging windows.

Telemetry schema v2 separates raw dBFS diagnostics from nullable acoustic
metrics. Uncalibrated input does not populate SPL fields. Device and WAV data
remain explicitly unverified throughout this hardware-test release. Importing
a vendor file applies its frequency response but does not guess sensitivity
scaling. A documented 1 kHz reference enables provisional acoustic values.

Keep layout preferences in each browser's local storage. Width, height, digit
size, spacing, descriptions, spectrum visibility, and horizontal/vertical
placement do not alter measurement state. `/display` is the dedicated strip
route; its controls open in a full-window dialog even at shallow heights.

## Consequences

- Real hardware validation remains required before operational SPL use.
- Every client sees one measurement state; slow clients cannot queue audio.
- Gaps reset rolling windows instead of silently interpolating missing audio.
- Recovery may lose the final uncommitted logging interval, not an entire event.
- Audience correction is currently A-only; peak estimation is deliberately absent.
- No raw audio recordings or uploads; WAV fixtures must already exist locally.
- The LAN appliance serves all assets locally. A manifest supports a home-screen
  shortcut, but no service-worker/offline-shell installation claim is made.
- iPadOS controls browser-window placement; the app controls content within it.
- This release assumes a trusted event LAN. Same-origin mutation checks prevent
  browser cross-origin changes; they are not user authentication.
