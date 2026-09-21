# Microphone placement and audience estimation

## Preferred fixed mounting

For standing events, start near 1.5 m / 5 ft above the floor. Aim the UMIK
upward and use its 90° calibration file.

Ranked practical options:

1. Boom-stand base at the side perimeter, boom extending 0.6-0.9 m / 2-3 ft
   into the audience area.
2. Super clamp and short boom on a sturdy post or railing, with the capsule
   clear of the mounting surface.
3. Clamp on a non-vibrating lighting stand at the room perimeter, secured with
   a safety and isolated from cable handling.
4. Rear/side operations table with the microphone extended well away from the
   tabletop, screen, and people.
5. Higher protected perimeter mount, followed by a measured correction to the
   audience reference zone.

Avoid corners, wall contact, speaker/subwoofer cabinets, vibrating truss, HVAC
outlets, and a position dominated by one nearby loudspeaker. Secure the stand,
cable, and computer against patrons and spills.

## Why geometry is insufficient

Speaker distance and polar data can estimate the direct field. Real venues add
reflections, boundary gain, room modes, subwoofer interference, audience
absorption, actual loudspeaker limiting, and frequency-dependent directivity.
Dimensions and specifications can choose candidate positions but cannot
reliably convert a poor fixed position into an audience average.

## Venue correction workflow

Create a measured profile for each materially different room/speaker layout:

1. Record 30 seconds of steady pink noise covering the system's useful bandwidth at the event mic position.
2. Move the same microphone through three representative audience
   locations without changing system level.
3. Include front/middle and house-left/right; exclude pathological wall/corner
   locations unless they are important occupied areas.
4. Return to the fixed mount and confirm the initial result is repeatable.
5. Energy-average the audience measurements (equal-energy, never a dB average).
6. Store the resulting single broadband **A-weighted** offset. The current
   implementation supports one A-weighted correction per profile — there is no
   C-weighted offset and no per-band correction curve. Mic C peak and the
   spectrum stay measured at the fixed microphone.

During a show, preserve and display both values:

```text
Measured at fixed mic:       91.8 dBA
Estimated audience average:  94.6 dBA
Venue profile correction:    +2.8 dB
```

Never rewrite the raw log with corrected values. Mark estimates clearly and
record profile identity with the event. Re-map after changing speaker location,
aiming, room orientation, or substantial audience layout.

## Choosing the reference zone

There is no single physical point equal to “the room average.” Define the goal
before mapping: average occupied audience exposure, loudest normal audience
zone, dance-floor average, or a venue-mandated position. For typical
band/social events, begin with an energy average of several occupied dance-floor
and nearby seating positions, while separately recording the loudest relevant
position.


## Guided UI

Audience level mapping is a visible dashboard card. Start with the fixed mic
position, capture three audience positions, then return to the fixed position.
Each button captures 30 seconds of host A-weighted energy. Set playback from
measured mic readings, not an existing estimate: aim for roughly **75–80 dBA at
an audience position**, staying at least **10 dB above background at every
position (preferably 15 dB)**; a quieter setup period is fine, show volume is
unnecessary. Keep external test playback, EQ and speaker setup unchanged; do not
handle the mic during a capture. The tool rejects clipping/input gaps and
fixed-check drift over 2 dB, and rejects a resulting offset outside ±30 dB. Apply
explicitly after naming the mapping. Each capture returns its level, actual
duration, calibration hash, applied offset and device — not a per-position
wall-clock time. The mapping's stored date (`mappedAt`) is the browser's apply
timestamp, not the moment any single position was measured.

Applying stores the profile in the durable appliance mapping library (name,
A-weighted offset, capture note, date) and enables the shared audience display.

The reading location (Measured at fixed microphone vs. Estimated audience) is
**shared across all clients** — the appliance owns it and publishes it in
telemetry, so a change on one browser follows on every connected strip after its
initial upgrade reload. It is not a browser-local setting. Audience mode maps
live, maximum live and both Leq values and is marked EST AUDIENCE; mic C peak,
spectrum and thresholds stay fixed-microphone data. No mapping shows blanks in
the estimated A fields.

Manage saved profiles from **Saved audience mappings**: sort by name, date or
correction, **Use selected mapping on all displays** to activate one, or **Clear
loaded mapping** to return every display to measured levels while keeping the
saved copy. Activating or clearing restarts averaging windows and requires
stopping any recording; toggling only the reading location does neither. A loaded
profile is protected from deletion — clear it first, then delete. Prior event
records always keep their original mapping. See ADR 0008 and ADR 0009.


The playback guidance above is a practical starting point, not a prescribed
absolute calibration level. [Rational Acoustics' SPL compensation guidance](https://support.rationalacoustics.com/support/solutions/articles/150000209715-how-to-use-spl-compensation)
recommends pink noise sufficiently above background for position comparison.
