"""Streaming DSP. Equations, conventions and tolerances: docs/dsp-implementation.md."""

from collections import deque
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy import signal

from .calibration import Calibration
from .models import Levels, Spectrum
from .spectrum import SpectrumAnalyzer

SAMPLE_RATE = 48000
BLOCK = 4800
OVERSAMPLE = 4
CENTRES = [
    25,
    31.5,
    40,
    50,
    63,
    80,
    100,
    125,
    160,
    200,
    250,
    315,
    400,
    500,
    630,
    800,
    1000,
    1250,
    1600,
    2000,
    2500,
    3150,
    4000,
    5000,
    6300,
    8000,
    10000,
    12500,
    16000,
]


def db(power: float) -> float | None:
    return float(10 * np.log10(power)) if power > 1e-30 else None


def weighting_sos(kind: Literal["A", "C"], sample_rate: int) -> NDArray[np.float64]:
    poles = (
        -2 * np.pi * np.array([20.6, 20.6, 12200, 12200] + ([107.7, 737.9] if kind == "A" else []))
    )
    zeros = np.zeros(4 if kind == "A" else 2)
    z, p, k = signal.bilinear_zpk(zeros, poles, (2 * np.pi * 12200) ** 2, sample_rate)
    sos = signal.zpk2sos(z, p, k)
    _, h = signal.sosfreqz(sos, worN=[1000], fs=sample_rate)
    sos[0, :3] /= abs(h[0])
    return sos


class EnergyWindow:
    """Exact rolling energy on fixed 100 ms boundaries, bounded memory."""

    def __init__(self, blocks: int):
        self.blocks = blocks
        self.values: deque[float] = deque()
        self.total = 0.0

    def add(self, mean_square: float) -> float:
        self.values.append(mean_square)
        self.total += mean_square
        if len(self.values) > self.blocks:
            self.total -= self.values.popleft()
        return max(0.0, self.total / len(self.values))


class Slow:
    def __init__(self, sample_rate: int):
        self.alpha = float(np.exp(-1 / sample_rate))
        self.state = np.zeros(1)

    def process(self, squares: NDArray[np.float64]) -> float:
        result, self.state = signal.lfilter(
            [1 - self.alpha], [1, -self.alpha], squares, zi=self.state
        )
        return float(result[-1])


class Processor:
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        calibration: Calibration | None = None,
        offset: float | None = None,
    ):
        if sample_rate != SAMPLE_RATE:
            raise ValueError("Only 48000 Hz input is supported; resample WAV fixtures explicitly")
        self.offset = offset
        self.correction = calibration.fir(sample_rate) if calibration else np.array([1.0])
        self.correction_state = np.zeros(len(self.correction) - 1)
        self.interpolator = signal.firwin(161, 1 / OVERSAMPLE, window=("kaiser", 8.6)) * 4
        self.interpolator_state = np.zeros(160)
        self.a = weighting_sos("A", sample_rate * OVERSAMPLE)
        self.c = weighting_sos("C", sample_rate * OVERSAMPLE)
        self.a_state = np.zeros((len(self.a), 2))
        self.c_state = np.zeros((len(self.c), 2))
        self.slow = Slow(sample_rate * OVERSAMPLE)
        self.minute = EnergyWindow(600)
        self.ten_minutes = EnergyWindow(6000)
        self.peak = 0.0
        self.max_slow_db: float | None = None
        self.blocks = 0
        _, reference_response = signal.freqz(self.correction, worN=[1000], fs=sample_rate)
        spectrum_offset = (
            offset + float(20 * np.log10(abs(reference_response[0])))
            if offset is not None
            else None
        )
        self.analyzer = SpectrumAnalyzer(calibration, spectrum_offset)
        self.spectrum = Spectrum()

    def reset_peak(self) -> None:
        self.peak = 0.0

    def correct_samples(self, samples: NDArray[np.float64]) -> NDArray[np.float64]:
        """Same causal FIR, computed with FFT convolution and input history."""
        if len(self.correction) == 1:
            return samples * self.correction[0]
        padded = np.concatenate((self.correction_state, samples))
        corrected = signal.fftconvolve(padded, self.correction, mode="valid")
        self.correction_state = padded[-(len(self.correction) - 1) :].copy()
        return corrected

    def process(self, samples: NDArray[np.float64]) -> tuple[Levels | None, Spectrum]:
        if samples.shape != (BLOCK,) or not np.isfinite(samples).all():
            raise ValueError("Expected 4800 finite mono samples")
        corrected = self.correct_samples(samples)
        up = np.zeros(BLOCK * OVERSAMPLE)
        up[::OVERSAMPLE] = corrected
        up, self.interpolator_state = signal.lfilter(
            self.interpolator, [1.0], up, zi=self.interpolator_state
        )
        a, self.a_state = signal.sosfilt(self.a, up, zi=self.a_state)
        c, self.c_state = signal.sosfilt(self.c, up, zi=self.c_state)
        squares = a * a
        slow = self.slow.process(squares)
        energy = float(np.mean(squares))
        minute = self.minute.add(energy)
        ten = self.ten_minutes.add(energy)
        self.peak = max(self.peak, float(np.max(c * c)))
        self.blocks += 1
        self.spectrum = self.analyzer.process(samples)
        if self.offset is None:
            return None, self.spectrum
        current_slow = db(slow)
        if current_slow is not None:
            current_slow += self.offset
            self.max_slow_db = (
                max(self.max_slow_db, current_slow)
                if self.max_slow_db is not None
                else current_slow
            )
        levels = [db(x) for x in (slow, minute, ten, self.peak)]
        return Levels(
            lasMaxDb=self.max_slow_db,
            **dict(
                zip(
                    ["lasDb", "laeq1Db", "laeq10Db", "lcpeakDb"],
                    [x + self.offset if x is not None else None for x in levels],
                    strict=True,
                )
            ),
        ), self.spectrum
