import math

import numpy as np
import pytest
from scipy import signal

from spl_dashboard.calibration import parse_calibration
from spl_dashboard.dsp import BLOCK, SAMPLE_RATE, EnergyWindow, Processor, Slow, db, weighting_sos


def analog_db(frequency, kind):
    # Independent direct frequency-domain evaluation of the published equations.
    def response(f):
        value = 12200**2 * f**2 / ((f**2 + 20.6**2) * (f**2 + 12200**2))
        if kind == "A":
            value *= f**2 / math.sqrt((f**2 + 107.7**2) * (f**2 + 737.9**2))
        return value

    return 20 * math.log10(response(frequency) / response(1000))


@pytest.mark.parametrize("kind", ["A", "C"])
@pytest.mark.parametrize(
    "frequency", [25, 31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 12500, 16000]
)
def test_frequency_weighting_reference(kind, frequency):
    _, response = signal.sosfreqz(weighting_sos(kind, 192000), worN=[frequency], fs=192000)
    assert 20 * np.log10(abs(response[0])) == pytest.approx(analog_db(frequency, kind), abs=0.35)


def sine(amplitude=0.1, frequency=1000):
    return amplitude * np.sin(2 * np.pi * frequency * np.arange(BLOCK) / SAMPLE_RATE)


def test_slow_analytic_step_and_decay():
    slow = Slow(SAMPLE_RATE)
    assert slow.process(np.ones(SAMPLE_RATE)) == pytest.approx(1 - math.exp(-1), abs=1e-9)
    assert slow.process(np.zeros(SAMPLE_RATE)) == pytest.approx(
        (1 - math.exp(-1)) * math.exp(-1), abs=1e-9
    )


def test_energy_average_and_exact_expiry():
    window = EnergyWindow(600)
    for _ in range(300):
        window.add(1)
    for _ in range(300):
        value = window.add(100)
    assert value == pytest.approx(50.5, abs=1e-10)
    assert db(value) == pytest.approx(17.032913781, abs=1e-8)
    for _ in range(300):
        value = window.add(100)
    assert value == pytest.approx(100, abs=1e-10)
    assert len(window.values) == 600


def test_ten_minute_window_is_bounded_and_warms():
    window = EnergyWindow(6000)
    for i in range(12000):
        value = window.add(1 if i < 6000 else 4)
    assert len(window.values) == 6000
    assert value == 4


def test_sine_levels_peak_hold_reset_and_rta():
    processor = Processor(offset=120)
    for _ in range(100):
        levels, spectrum = processor.process(sine())
    assert levels.lasDb == pytest.approx(96.9897, abs=0.03)
    assert levels.laeq1Db == pytest.approx(96.9897, abs=0.03)
    # Initial switch-on transient is legitimately held; compare steady sine after reset.
    processor.reset_peak()
    levels, _ = processor.process(sine())
    assert levels.lcpeakDb == pytest.approx(100, abs=0.05)
    assert spectrum.levelsDb[spectrum.centresHz.index(1000)] == pytest.approx(96.9897, abs=0.03)
    held = levels.lcpeakDb
    for _ in range(10):
        levels, _ = processor.process(sine(0.01))
    assert levels.lcpeakDb >= held
    held = levels.lcpeakDb
    for _ in range(10):
        levels, _ = processor.process(sine(0.01))
    assert levels.lcpeakDb == held
    processor.reset_peak()
    levels, _ = processor.process(sine(0.01))
    assert levels.lcpeakDb == pytest.approx(80, abs=0.05)


@pytest.mark.parametrize("frequency", [25, 125, 1000, 8000, 16000])
def test_end_to_end_weighted_sines(frequency):
    processor = Processor(offset=120)
    for i in range(50):
        t = (np.arange(BLOCK) + i * BLOCK) / SAMPLE_RATE
        levels, _ = processor.process(0.1 * np.sin(2 * np.pi * frequency * t))
    # Warm-up transient contributes under 0.03 dB to the five-second average.
    assert levels.laeq1Db == pytest.approx(96.9897 + analog_db(frequency, "A"), abs=0.35)


def test_scaling_silence_uncalibrated_and_invalid_input():
    assert Processor().process(sine())[0] is None
    assert db(0) is None
    p1, p2 = Processor(offset=120), Processor(offset=120)
    for _ in range(10):
        a, _ = p1.process(sine(0.1))
        b, _ = p2.process(sine(0.01))
    assert a.laeq1Db - b.laeq1Db == pytest.approx(20, abs=0.01)
    assert Processor(offset=120).process(np.zeros(BLOCK))[0].lasDb is None
    for rate in [44100, 96000]:
        with pytest.raises(ValueError, match="48000"):
            Processor(sample_rate=rate)
    with pytest.raises(ValueError, match="finite"):
        p1.process(np.full(BLOCK, np.nan))


def test_calibration_parser_hash_and_flat_correction():
    text = '"Sens Factor =-12.3dB, SERNO: 7001234"\n20 6\n1000 6\n20000 6\n'
    cal = parse_calibration(text)
    assert cal.serial == "7001234"
    assert cal.sensitivity == -12.3
    assert len(cal.digest) == 64
    processor = Processor(calibration=cal, offset=120)
    for _ in range(100):
        level, _ = processor.process(sine())
    assert level.laeq1Db == pytest.approx(90.9897, abs=0.03)


@pytest.mark.parametrize(
    "text",
    [
        "hello",
        "20 0",
        "20 0\n10 1",
        "20 0\n20 1",
        "0 0\n100 0",
        "20 nan\n100 0",
        "20 nope\n100 0",
        "20 31\n100 0",
    ],
)
def test_malformed_calibration(text):
    with pytest.raises(ValueError):
        parse_calibration(text)


def test_broadband_noise_against_frequency_domain_energy():
    samples = np.random.default_rng(12345).normal(0, 0.05, SAMPLE_RATE * 10)
    frequencies = np.fft.rfftfreq(len(samples), 1 / SAMPLE_RATE)
    f = frequencies[1:]
    response = (
        12200**2
        * f**4
        / (
            (f * f + 20.6**2)
            * (f * f + 12200**2)
            * np.sqrt((f * f + 107.7**2) * (f * f + 737.9**2))
        )
    )
    norm = (
        12200**2
        * 1000**4
        / (
            (1000**2 + 20.6**2)
            * (1000**2 + 12200**2)
            * math.sqrt((1000**2 + 107.7**2) * (1000**2 + 737.9**2))
        )
    )
    powers = abs(np.fft.rfft(samples)) ** 2 / len(samples) ** 2
    powers[1:-1] *= 2
    expected = 10 * math.log10(float(np.sum(powers[1:] * (response / norm) ** 2))) + 120
    processor = Processor(offset=120)
    for block in samples.reshape(-1, BLOCK):
        levels, _ = processor.process(block)
    assert levels.laeq1Db == pytest.approx(expected, abs=0.2)


def test_invalid_sensitivity_header_rejected():
    with pytest.raises(ValueError, match="sensitivity"):
        parse_calibration('"Sens Factor =nonsense dB"\n20 0\n20000 0')


def test_detailed_analyzer_energy_and_update_cadence():
    processor = Processor(offset=120)
    for _ in range(20):
        previous = processor.spectrum
        _, spectrum = processor.process(sine(0.1, 1000) + sine(0.01, 4000))
        assert spectrum is not previous  # Every 100 ms capture block, not 500 ms.
    assert len(spectrum.traceCentresHz) == 113
    i = spectrum.traceCentresHz.index(1000)
    assert spectrum.traceLevelsDb[i] == pytest.approx(96.9897, abs=0.03)
    j = int(np.argmin(abs(np.array(spectrum.traceCentresHz) - 4000)))
    assert spectrum.traceLevelsDb[j] == pytest.approx(76.9897, abs=0.03)
    # Disjoint FFT bands conserve the energy of both reference tones.
    total = sum(10 ** ((v - 120) / 10) for v in spectrum.traceLevelsDb if v is not None)
    assert total == pytest.approx((0.1**2 + 0.01**2) / 2, rel=0.001)


def test_maximum_live_tracks_slow_levels_not_pressure_peaks():
    processor = Processor(offset=120)
    seen = []
    for amplitude in [0.1] * 30 + [0.01] * 30:
        levels, _ = processor.process(sine(amplitude))
        seen.append(levels.lasDb)
        assert levels.lasMaxDb == max(seen)
    assert levels.lasMaxDb > levels.lasDb + 10
    processor.max_slow_db = None
    levels, _ = processor.process(sine(0.01))
    assert levels.lasMaxDb == levels.lasDb


def test_fft_calibration_filter_matches_direct_causal_fir_across_blocks():
    calibration = parse_calibration("10 -3\n100 6\n1000 0\n10000 -5\n24000 2")
    processor = Processor(calibration=calibration, offset=120)
    samples = np.random.default_rng(18).normal(0, 0.1, BLOCK * 12)
    samples[BLOCK - 1] = 1
    samples[BLOCK * 3] = -1
    expected = signal.lfilter(processor.correction, [1.0], samples)
    actual = np.concatenate([processor.correct_samples(b) for b in np.split(samples, 12)])
    np.testing.assert_allclose(actual, expected, atol=1e-12, rtol=1e-10)
