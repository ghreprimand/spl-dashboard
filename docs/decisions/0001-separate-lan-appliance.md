# ADR 0001: Separate LAN measurement appliance

- Status: accepted
- Date: 2026-09-20

## Decision

Build SPL Dashboard as a separate project and headless LAN appliance,
not as a Mixing Station plug-in or a page that captures the iPad microphone.

The Linux host owns audio capture, measurement state, logging, and exports. The
iPad browser is a disposable client. The dashboard remains operational without any public website or internet
connection.

## Rationale

- Mixing Station does not expose arbitrary acoustic telemetry in custom layouts.
- The tablet moves around, while meaningful SPL monitoring needs a fixed and
  documented microphone position.
- Browser suspension must not interrupt Leq windows or logs.
- A local service can use the UMIK calibration file and expose the same data to
  multiple displays.
- Separation avoids coupling a safety-adjacent measurement service to the
  published guide's static deployment.

## Consequences

- Another device must remain powered near the UMIK.
- The project must package Linux audio and service startup reliably.
- The compact dashboard lives beside, rather than inside, Mixing Station.
- Remote clients can reconnect without losing measurements.
