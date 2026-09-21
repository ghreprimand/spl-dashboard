#!/usr/bin/env python3
"""Create synthetic local PCM fixtures, never a recording of an event."""
import argparse
import math
import struct
import wave
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path)
parser.add_argument('--seconds', type=int, default=30)
parser.add_argument('--frequency', type=float, default=1000)
parser.add_argument('--peak-dbfs', type=float, default=-20)
args = parser.parse_args()
if not 1 <= args.seconds <= 3600 or not 20 <= args.frequency <= 20000 or not -100 <= args.peak_dbfs <= 0:
    parser.error('Use 1–3600 seconds, 20–20000 Hz, and -100–0 peak dBFS')
args.output.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(args.output), 'wb') as out:
    out.setnchannels(1)
    out.setsampwidth(3)
    out.setframerate(48000)
    amplitude = (2**23 - 1) * 10 ** (args.peak_dbfs / 20)
    for second in range(args.seconds):
        values = bytearray()
        for sample in range(48000):
            integer = round(amplitude * math.sin(2 * math.pi * args.frequency * (second + sample/48000)))
            values.extend(struct.pack('<i', integer)[:3])
        out.writeframes(values)
print(f'{args.output}: {args.frequency:g} Hz, raw RMS approximately {args.peak_dbfs - 3.0103:.4f} dBFS')
