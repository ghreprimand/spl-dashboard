# Research notes and primary references

## Confirmed product context

- Mixing Station is a mixer remote and does not play/capture audio for acoustic
  measurement. Its custom layouts expose app/mixer actions and values:
  https://mixingstation.app/ms-docs/custom-layouts/
- Open Sound Meter demonstrates the desired numeric/SPL/spectrum interface and
  supports desktop Linux plus network sharing between instances:
  https://opensoundmeter.com/static/manuals/v1.5.pdf
- Smaart SPL demonstrates the desired metric set, logging, alarms, and browser
  remote viewing; it also states that accurate SPL requires appropriate
  calibration hardware:
  https://www.rationalacoustics.com/products/smaart-spl-v9-perpetual
- miniDSP publishes UMIK-1 sample format, USB class, maximum level, unique
  calibration, and 3/8-inch mount details:
  https://www.minidsp.com/products/acoustic-measurement/umik-1
- REW recognises UMIK sensitivity calibration and is a useful comparison tool:
  https://www.roomeqwizard.com/betahelp/help/html/calsoundcard.html

## Licensing caution

Open Sound Meter is GPL-licensed. Treat its interface and documented behaviour
as product research. Do not copy its implementation into a differently licensed
project without an explicit licensing decision.
