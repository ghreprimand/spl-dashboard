"""Calibration file parsing; vendor sensitivity is retained, never guessed."""

import hashlib
import re
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import signal


@dataclass(frozen=True)
class Calibration:
    digest: str
    serial: str | None
    sensitivity: float | None
    frequencies: NDArray[np.float64]
    response: NDArray[np.float64]
    analog_gain: float | None = None

    def fir(self, sample_rate: int) -> NDArray[np.float64]:
        # Vendor data is measured response, so correction has the opposite sign.
        grid = np.linspace(0, sample_rate / 2, 8193)
        response = np.interp(
            np.log10(np.maximum(grid, 1)), np.log10(self.frequencies), self.response
        )
        return signal.firwin2(2049, grid, 10 ** (-response / 20), fs=sample_rate)


def parse_calibration(text: str) -> Calibration | None:
    if not text.strip():
        return None
    if len(text) > 200000:
        raise ValueError("Calibration file exceeds 200 kB")
    sensitivity = re.search(r"Sens\s+Factor\s*=\s*([-+\d.eE]+)\s*dB", text, re.I)
    if re.search(r"Sens\s+Factor", text, re.I) and not sensitivity:
        raise ValueError("Invalid sensitivity factor header")
    analog_gain = re.search(r"AGain\s*=\s*([-+\d.eE]+)\s*dB", text, re.I)
    if re.search(r"AGain", text, re.I) and not analog_gain:
        raise ValueError("Invalid analog gain header")
    file_gain = float(analog_gain[1]) if analog_gain else None
    if file_gain is not None and (not np.isfinite(file_gain) or not 0 <= file_gain <= 60):
        raise ValueError("Invalid analog gain")
    serial = re.search(r"SERNO\s*:\s*([\w-]+)", text, re.I)
    points: list[tuple[float, float]] = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line[0] not in "+-.0123456789":
            continue
        columns = line.replace(",", " ").split()
        try:
            frequency, gain = float(columns[0]), float(columns[1])
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Invalid calibration data on line {number}") from exc
        if not np.isfinite([frequency, gain]).all() or not 0 < frequency <= 96000:
            raise ValueError(f"Invalid frequency or gain on line {number}")
        if abs(gain) > 30:
            raise ValueError("Calibration response exceeds ±30 dB; inspect the file")
        if points and frequency <= points[-1][0]:
            raise ValueError("Calibration frequencies must be strictly increasing")
        points.append((frequency, gain))
    if len(points) < 2:
        raise ValueError("Calibration requires at least two frequency/response pairs")
    sens = float(sensitivity[1]) if sensitivity else None
    if sens is not None and (not np.isfinite(sens) or not -100 <= sens <= 40):
        raise ValueError("Invalid sensitivity factor")
    values = np.asarray(points, dtype=np.float64)
    return Calibration(
        hashlib.sha256(text.encode()).hexdigest(),
        serial[1] if serial else None,
        sens,
        values[:, 0],
        values[:, 1],
        file_gain,
    )


@dataclass(frozen=True)
class InputCalibration:
    """Evidence from the selected device, not from a browser-supplied offset."""

    supported_umik: bool = False
    direct_pcm: bool = False
    analog_gain_db: float | None = None
    digital_gain_db: float | None = None
    usb_serial: str | None = None
    binding: str = "name"
    reason: str = "Waiting for the selected microphone"


def serial_digits(serial: str | None) -> str:
    return re.sub(r"[^0-9]", "", serial or "")


def usable_serial(serial: str | None) -> bool:
    digits = serial_digits(serial)
    return bool(digits and set(digits) != {"0"})


def umik_file_offset(
    calibration: Calibration | None, device: InputCalibration, confirmed_serial: str = ""
) -> tuple[float | None, str]:
    """UMIK-1 direct PCM convention; see docs/umik-sensitivity.md.

    Full-scale sample magnitude is 1; full-scale sine RMS is -3.0103 dBFS.
    The internal analog gain is already included in the supplied sensitivity.
    Only a difference from the file's gain is compensated, never the gain twice.
    """
    if calibration is None or calibration.sensitivity is None:
        return None, "Load the microphone's calibration file with its Sens Factor"
    if not device.supported_umik or not device.direct_pcm:
        return None, device.reason
    if device.analog_gain_db is None or device.digital_gain_db is None:
        return None, "Input gain could not be verified; use an explicit acoustic reference"
    serial = serial_digits(calibration.serial)
    if not serial:
        return None, "The calibration file has no microphone serial"
    if usable_serial(device.usb_serial):
        if serial_digits(device.usb_serial) != serial:
            return None, "Calibration file serial does not match the connected microphone"
    elif serial_digits(confirmed_serial) != serial:
        return None, "Confirm that the file serial matches the label on this microphone"
    reference_gain = calibration.analog_gain if calibration.analog_gain is not None else 18.0
    offset = (
        124.0
        - calibration.sensitivity
        + reference_gain
        - device.analog_gain_db
        - device.digital_gain_db
    )
    return offset, "Calibrated to the supplied UMIK-1 sensitivity file"
