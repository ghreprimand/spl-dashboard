import math

import numpy as np
import pytest
from scipy.signal import periodogram

from spl_dashboard.calibration import parse_calibration
from spl_dashboard.spectrum import HOP, RATE, SpectrumAnalyzer, band_geometry, integrate_bands


def feed(analyzer, frequency=1000, amplitude=0.1, blocks=40):
    for i in range(blocks):
        t = (np.arange(HOP) + i * HOP) / RATE
        result = analyzer.process(amplitude * np.sin(2 * np.pi * frequency * t))
    return result


@pytest.mark.parametrize("fraction", [3, 6, 12])
def test_fractional_cells_conserve_power_and_cover_endpoints(fraction):
    centres, edges = band_geometry(fraction)
    assert edges[0] < 20 and edges[-1] > 20000 and edges[-1] < RATE / 2
    assert np.all(np.diff(edges) > 0)
    assert 1000 in centres
    df = 0.5
    power = np.random.default_rng(12).random(48001)
    actual = integrate_bands(power, df, edges)
    frequency = np.arange(len(power)) * df
    expected = []
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        overlap = (
            np.maximum(0, np.minimum(frequency + df / 2, b) - np.maximum(frequency - df / 2, a))
            / df
        )
        expected.append(np.sum(power * overlap))
    np.testing.assert_allclose(actual, expected, rtol=1e-10)
    assert sum(actual) == pytest.approx(integrate_bands(power, df, edges[[0, -1]])[0], rel=1e-10)


def test_against_independent_scipy_periodogram():
    rng = np.random.default_rng(81)
    samples = rng.normal(0, 0.03, RATE * 2)
    analyzer = SpectrumAnalyzer(None, 100)
    for block in np.split(samples, 40):
        result = analyzer.process(block)
    for band in result.bands:
        power = np.zeros(len(band.centresHz))
        for n, weights in analyzer.band_weights[band.fraction].items():
            freqs, density = periodogram(samples[-n:], fs=RATE, window=np.hanning(n), detrend=False)
            df = freqs[1] - freqs[0]
            power += weights * integrate_bands(density * df, df, np.array(band.edgesHz))
        np.testing.assert_allclose(band.levelsDb, 100 + 10 * np.log10(power), atol=1e-10)


def test_hann_low_tone_leakage_matches_analytic_three_bin_energy():
    result = feed(SpectrumAnalyzer(None, 0), 25)
    band = result.bands[2]
    i = int(np.argmin(abs(np.array(band.centresHz) - 25)))
    # A coherent Hann-windowed sine puts 1/6, 2/3, 1/6 of its energy in 3 bins.
    expected = 0.0
    for f, share in [(24.5, 1 / 6), (25, 2 / 3), (25.5, 1 / 6)]:
        overlap = max(0, min(f + 0.25, band.edgesHz[i + 1]) - max(f - 0.25, band.edgesHz[i])) / 0.5
        expected += 0.1**2 / 2 * share * overlap
    assert band.levelsDb[i] == pytest.approx(10 * math.log10(expected), abs=0.003)


def test_warmup_silence_and_new_identity():
    a = SpectrumAnalyzer(None, None)
    for i in range(40):
        result = a.process(np.zeros(HOP))
        assert result.bands[0].ready == (i >= 19)
        assert result.bands[2].ready == (i >= 39)
        for band in result.bands:
            assert all(v is None for v in band.levelsDb)
    assert result.unit == "dBFS"
    assert result.analysisId != SpectrumAnalyzer(None, None).identity


@pytest.mark.parametrize("frequency", [50, 125, 1000, 8000, 16000])
def test_direct_file_correction_and_flat_reference(frequency):
    # Log-linear response, exactly +6 dB per decade relative to 1 kHz.
    calibration = parse_calibration("10 -12\n100 -6\n1000 0\n10000 6\n24000 8.28126745")
    a = feed(SpectrumAnalyzer(calibration, 120), frequency)
    b = feed(SpectrumAnalyzer(None, 120), frequency)
    pa = sum(10 ** (v / 10) for v in a.bands[2].levelsDb if v is not None)
    pb = sum(10 ** (v / 10) for v in b.bands[2].levelsDb if v is not None)
    assert 10 * np.log10(pa / pb) == pytest.approx(-6 * np.log10(frequency / 1000), abs=0.05)
    flat = parse_calibration("10 6\n24000 6")
    c = feed(SpectrumAnalyzer(flat, 120), frequency)
    assert c.bands[2].levelsDb == b.bands[2].levelsDb


def test_stable_average_is_power_not_decibels():
    a = SpectrumAnalyzer(None, 0)
    feed(a, blocks=40)
    before = a.averages[6].copy()
    result = a.process(np.zeros(HOP))
    bands = result.bands[1]
    current = np.array([10 ** (v / 10) if v is not None else 0 for v in bands.levelsDb])
    expected = before + (1 - np.exp(-0.05)) * (current - before)
    np.testing.assert_allclose(a.averages[6], expected, rtol=1e-10)


def test_flat_density_and_pink_density_band_trends():
    centres, edges = band_geometry(6)
    freqs = np.arange(48001) * 0.5
    white = integrate_bands(np.ones_like(freqs), 0.5, edges)
    # White noise energy rises with band width; pink noise is flat per octave.
    np.testing.assert_allclose(
        white / centres, np.full_like(centres, white[0] / centres[0]), rtol=1e-10
    )
    pink = integrate_bands(1 / np.maximum(freqs, 0.5), 0.5, edges)
    assert np.ptp(10 * np.log10(pink)) < 0.02


@pytest.mark.parametrize("frequency", [999.5, 1000.25, 1029.2, 1059.25, 1122.1])
def test_tones_across_bins_and_band_boundaries_conserve_total(frequency):
    result = feed(SpectrumAnalyzer(None, 0), frequency)
    for bands in result.bands:
        energy = sum(10 ** (v / 10) for v in bands.levelsDb if v is not None)
        assert 10 * np.log10(energy) == pytest.approx(10 * np.log10(0.1**2 / 2), abs=0.03)


def test_weak_band_is_not_lost_beside_strong_tone():
    power = np.zeros(100)
    power[10] = 1
    power[70] = 1e-22
    energy = integrate_bands(power, 1, np.array([5.5, 20.5, 60.5, 80.5]))
    assert energy[0] == 1
    assert energy[2] == pytest.approx(1e-22, rel=1e-12, abs=0)


def test_high_bands_respond_in_100ms_without_shortening_bass_window():
    a = SpectrumAnalyzer(None, 0)
    for _ in range(40):
        a.process(np.zeros(HOP))
    for i in range(2):
        t = (np.arange(HOP) + i * HOP) / RATE
        result = a.process(0.1 * np.sin(2 * np.pi * 4000 * t) + 0.1 * np.sin(2 * np.pi * 25 * t))
    fine = result.bands[2]
    high = int(np.argmin(abs(np.array(fine.centresHz) - 4000)))
    low = int(np.argmin(abs(np.array(fine.centresHz) - 25)))
    assert fine.windowSecondsByBand[high] == 0.1
    assert fine.windowSecondsByBand[low] == 2
    assert fine.levelsDb[high] == pytest.approx(-23.0103, abs=0.03)
    assert fine.levelsDb[low] < fine.levelsDb[high] - 20
    assert result.sequence == 42
    for weights in a.band_weights.values():
        np.testing.assert_allclose(sum(weights.values()), 1, atol=1e-12)


def test_vectorized_projector_matches_reference_including_empty_and_edge_cells():
    from spl_dashboard.spectrum import BandProjector

    power = np.random.default_rng(44).random(100)
    power[10] = 1e18
    edges = np.array([-0.5, 0.5, 0.6, 1.1, 1.5, 5.5, 10.5, 11.5, 22.1, 49.9, 50, 99.5])
    expected = integrate_bands(power, 1, edges)
    actual = BandProjector(edges, 1, len(power)).apply(power)
    np.testing.assert_allclose(actual, expected, rtol=1e-12)
