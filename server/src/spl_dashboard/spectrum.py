"""Power-conserving FFT band analysis. See docs/spectrum-analyzer.md."""

from collections import deque
from uuid import uuid4

import numpy as np
from numpy.typing import NDArray
from scipy.fft import rfft

from .calibration import Calibration
from .models import Spectrum, SpectrumBands

RATE = 48000
HOP = 2400
WINDOW_SIZES = (4800, 12000, 24000, 48000, 96000)


def integrate_bands(
    power: NDArray[np.float64], bin_hz: float, edges: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Integrate piecewise-constant FFT-bin power with fractional edge coverage.

    Each bin represents a cell centred on its frequency. This reduces boundary
    quantization for noise; it does not undo window leakage or resolve new tones.
    """
    positions = np.clip(edges / bin_hz + 0.5, 0, len(power))
    result = np.zeros(len(edges) - 1)
    for k, (a, b) in enumerate(zip(positions[:-1], positions[1:], strict=True)):
        first, last = int(a), int(b)
        if first == last:
            result[k] = power[first] * (b - a) if first < len(power) else 0
        else:
            # Local sums preserve weak bands beside strong tones; subtracting
            # large cumulative totals would lose small powers to cancellation.
            result[k] = power[first] * (first + 1 - a)
            result[k] += np.sum(power[first + 1 : last])
            if last < len(power):
                result[k] += power[last] * (b - last)
    return result


class BandProjector:
    """Precomputed fractional cells with vectorized local reductions."""

    def __init__(self, edges: NDArray[np.float64], bin_hz: float, length: int):
        positions = np.clip(edges / bin_hz + 0.5, 0, length)
        self.first = positions[:-1].astype(np.int64)
        self.last = positions[1:].astype(np.int64)
        self.same = self.first == self.last
        self.first_weight = np.where(self.same, np.diff(positions), self.first + 1 - positions[:-1])
        self.last_weight = np.where(self.same, 0, positions[1:] - self.last)
        self.cuts = np.column_stack((np.minimum(self.first + 1, length), self.last)).ravel()
        self.interior = self.last > self.first + 1

    def apply(self, power: NDArray[np.float64]) -> NDArray[np.float64]:
        # The sentinel makes upper boundary indices valid without special cases.
        padded = np.append(power, 0.0)
        middle = np.add.reduceat(padded, self.cuts)[::2]
        return (
            padded[self.first] * self.first_weight
            + padded[self.last] * self.last_weight
            + np.where(self.interior, middle, 0.0)
        )


def band_geometry(fraction: int) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    # Base-ten octave approximation, anchored at 1 kHz; no IEC filter-bank claim.
    per_decade = fraction * 10 / 3
    indices = np.arange(round(-1.7 * per_decade), round(1.3 * per_decade) + 1)
    centres = 1000 * 10 ** (indices / per_decade)
    ratio = 10 ** (0.5 / per_decade)
    return centres, np.concatenate((centres / ratio, [centres[-1] * ratio]))


class SpectrumAnalyzer:
    def __init__(self, calibration: Calibration | None, offset: float | None):
        self.offset = offset
        self.identity = uuid4().hex
        self.blocks: deque[NDArray[np.float64]] = deque(maxlen=40)
        self.sequence = 0
        self.windows: dict[int, NDArray[np.float64]] = {}
        self.gains: dict[int, NDArray[np.float64]] = {}
        self.geometry = {fraction: band_geometry(fraction) for fraction in (3, 6, 12)}
        self.averages: dict[int, NDArray[np.float64]] = {}
        self.band_sizes: dict[int, NDArray[np.int64]] = {}
        self.band_weights: dict[int, dict[int, NDArray[np.float64]]] = {}
        self.normalization: dict[int, float] = {}
        self.projectors: dict[tuple[int, int], tuple[NDArray[np.int64], BandProjector]] = {}
        for fraction, (_, edges) in self.geometry.items():
            maximum = RATE * (2 if fraction == 12 else 1)
            choices = [n for n in WINDOW_SIZES if n <= maximum]
            desired = np.clip(6 * RATE / np.diff(edges), choices[0], choices[-1])
            lower = np.array([max(n for n in choices if n <= target) for target in desired])
            upper = np.array([min(n for n in choices if n >= target) for target in desired])
            blend = np.zeros(len(desired))
            different = lower != upper
            blend[different] = np.log(desired[different] / lower[different]) / np.log(
                upper[different] / lower[different]
            )
            self.band_sizes[fraction] = upper.astype(np.int64)
            self.band_weights[fraction] = {
                n: (lower == n) * (1 - blend) + (upper == n) * blend for n in choices
            }
        for fraction, weights_by_size in self.band_weights.items():
            edges = self.geometry[fraction][1]
            for size, weights in weights_by_size.items():
                indices = np.flatnonzero(weights > 0)
                if len(indices):
                    self.projectors[fraction, size] = (
                        indices,
                        BandProjector(
                            edges[indices[0] : indices[-1] + 2], RATE / size, size // 2 + 1
                        ),
                    )
        for size in WINDOW_SIZES:
            self.windows[size] = np.hanning(size)
            self.normalization[size] = float(size * np.sum(self.windows[size] ** 2))
            frequencies = np.fft.rfftfreq(size, 1 / RATE)
            correction = np.zeros_like(frequencies)
            if calibration:
                reference = np.interp(
                    np.log10(1000), np.log10(calibration.frequencies), calibration.response
                )
                correction = reference - np.interp(
                    np.log10(np.maximum(frequencies, 1)),
                    np.log10(calibration.frequencies),
                    calibration.response,
                )
            self.gains[size] = 10 ** (correction / 10)

    def process(self, samples: NDArray[np.float64]) -> Spectrum:
        if (
            samples.ndim != 1
            or len(samples) not in (HOP, 2 * HOP)
            or not np.isfinite(samples).all()
        ):
            raise ValueError("Expected 2400 or 4800 finite samples")
        for start in range(0, len(samples), HOP):
            self.blocks.append(samples[start : start + HOP].copy())
        self.sequence += len(samples) // HOP
        spectra: dict[int, NDArray[np.float64]] = {}
        buffered = np.concatenate(list(self.blocks))
        for size in WINDOW_SIZES:
            if len(self.blocks) * HOP < size:
                continue
            data = buffered[-size:]
            window = self.windows[size]
            power = np.abs(rfft(data * window)) ** 2 / self.normalization[size]
            power[1:-1] *= 2
            spectra[size] = power * self.gains[size]
        result = Spectrum(
            updateHz=round(RATE / len(samples)),
            analysisId=self.identity,
            sequence=self.sequence,
            unit="dB SPL" if self.offset is not None else "dBFS",
            method=(
                "Multiresolution Hann FFT; fractional bin integration; "
                "normalized file correction; unweighted"
            ),
        )
        for fraction, (centres, edges) in self.geometry.items():
            sizes = self.band_sizes[fraction]
            size = int(np.max(sizes))
            levels: list[float | None] = []
            smoothed: list[float | None] = []
            if size in spectra:
                energy = np.zeros(len(centres))
                for length, weights in self.band_weights[fraction].items():
                    group = self.projectors.get((fraction, length))
                    if group:
                        indices, projector = group
                        energy[indices] += weights[indices] * projector.apply(spectra[length])
                previous = self.averages.get(fraction, energy)
                average = previous + (-np.expm1(-len(samples) / RATE)) * (energy - previous)
                self.averages[fraction] = average

                def convert(values: NDArray[np.float64]) -> list[float | None]:
                    return [
                        float(10 * np.log10(v) + (self.offset or 0)) if v > 1e-30 else None
                        for v in values
                    ]

                levels, smoothed = convert(energy), convert(average)
            result.bands.append(
                SpectrumBands(
                    fraction=fraction,
                    centresHz=centres.tolist(),
                    edgesHz=edges.tolist(),
                    levelsDb=levels,
                    smoothedLevelsDb=smoothed,
                    windowSeconds=size / RATE,
                    minWindowSeconds=float(np.min(sizes) / RATE),
                    windowSecondsByBand=(sizes / RATE).tolist(),
                    ready=size in spectra,
                )
            )
        # Backwards-compatible fields for older clients and exported records.
        third, _, detail = result.bands
        if third.ready:
            result.centresHz = [
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
            result.levelsDb = third.levelsDb[1:-1]
        if detail.ready:
            result.traceCentresHz = detail.centresHz[4:-4]
            result.traceLevelsDb = detail.levelsDb[4:-4]
        return result
