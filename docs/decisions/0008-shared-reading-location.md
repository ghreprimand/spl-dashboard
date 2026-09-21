# ADR 0008: Shared reading location and visible mapping identity

Status: accepted

Audience corrections and all five capture records already persist in the appliance
SQLite configuration (audienceMappingNote) and event snapshots. A second mapping
file is unnecessary. The defect was a browser-local audience display selection.

Persist audienceDisplay on the appliance and publish readingLocation (audience,
name, offsetDb, mappedAt) in every telemetry frame. Applying a guided mapping sets
this shared choice to audience. Connected clients use telemetry as truth and
ignore the obsolete localStorage audience flag. Size and position remain local.
Existing mapped installations without a saved choice default to audience; unmapped
installations default to measured. Unknown dates are shown as unavailable, never
invented. The existing capture-note date is the mapping creation/apply timestamp.

PUT /api/reading-location changes only the display choice, under the configuration
lock and existing origin protection. It is allowed during recording, persists
without capture restart, and does not alter measurements, estimates, map or event
configuration. Applying a different mapping still requires stopping the event.
No mapping means audience selection is rejected. Missing estimates remain blank.

The strip identifies the venue, correction and compact date/time. Controls show
full local date/time and shared-state scope. Raw logs, C peak, spectrum and alarm
thresholds remain fixed-microphone data. The calibration math is unchanged.

Verify two WebSocket clients receive the same mapping, choice persists across
restart, display toggling does not reset analysis or stop logging, and browser
localStorage cannot override server state. A connected older UI needs one reload
to adopt the new shared behavior.
