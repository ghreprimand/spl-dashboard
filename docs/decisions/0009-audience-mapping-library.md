# ADR 0009: Durable audience mapping library

Status: accepted

Store immutable mapping snapshots in a new additive audience_mappings SQLite
table. Each contains name, correction, full capture note and creation timestamp.
A content-derived ID deduplicates repeat saves of exactly the same mapping;
new captures with the same name remain separate dated versions. Migrate the
existing active map idempotently at startup. Older overwritten maps cannot be
recovered unless another record already retained them; do not invent entries.

Applying a saved profile copies only its three mapping fields into current
settings under the configuration lock and enables the shared audience display.
It preserves current microphone/calibration/input settings. As with new mappings,
activation requires stopping recording and restarts input/averages. Event snapshots
and raw telemetry remain immutable. Reading-location telemetry includes mappingId
so clients agree on the loaded profile, not merely a potentially duplicated name.

The selector lists name, capture/apply date and correction. Sorting is browser-local:
newest, oldest, name, or correction. Null legacy dates remain explicitly unknown.
Library changes refresh in other open dashboards within five seconds. Active
profile updates still arrive immediately through telemetry.

Deletion requires an explicit confirmation naming the selected profile. The API
rejects deletion of the loaded profile (even with audience display off); clear it or apply
another profile first. Deleting an inactive profile removes its library entry
only, preserving prior event snapshots/logs. Same-origin write protection applies.

Tests cover legacy migration, deduplication, retaining same-name versions,
activation/persistence, recording guards, protection of loaded profiles, confirmed
delete and sorting. No new measurement math or audio transport is introduced.

## Clearing the loaded mapping (0.4.4)

POST /api/audience-mapping/clear explicitly unloads the profile and selects measured
readings on every display. It clears only mapping fields, preserves the library
entry, and uses the same configuration lock and recording guard as activation.
Averages restart. An operator can then select and delete that saved entry, even
if it is the only mapping. Historical event configurations remain unchanged.
