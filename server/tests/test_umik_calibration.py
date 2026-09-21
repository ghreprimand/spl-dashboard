"""Reference vectors for the documented UMIK-1 direct PCM sensitivity convention."""

import asyncio
from dataclasses import replace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from spl_dashboard.calibration import InputCalibration, parse_calibration, umik_file_offset
from spl_dashboard.capture import inspect_calibration_input
from spl_dashboard.dsp import BLOCK, SAMPLE_RATE, Processor, db
from spl_dashboard.models import Settings
from spl_dashboard.runtime import Runtime

PROFILE = InputCalibration(
    supported_umik=True,
    direct_pcm=True,
    analog_gain_db=18,
    digital_gain_db=0,
    usb_serial="000-0000",
    binding="usb-port",
)
# Synthetic serial and sensitivity; not a real microphone calibration.
FILE = '"Sens Factor =-0.250dB, SERNO: 1234567"\n20 0\n1000 0\n20000 0\n'


def test_vendor_offset_reference_and_no_double_analog_gain():
    cal = parse_calibration(FILE)
    offset, _ = umik_file_offset(cal, PROFILE, "1234567")
    assert offset == pytest.approx(124.250)
    assert -30.250 + offset == pytest.approx(94.0)
    # Gain in the file is already included. Only the change is compensated.
    assert umik_file_offset(cal, replace(PROFILE, analog_gain_db=12), "1234567")[
        0
    ] == pytest.approx(130.250)
    cal = parse_calibration(FILE.replace("SERNO:", "AGain =12dB, SERNO:"))
    assert umik_file_offset(cal, replace(PROFILE, analog_gain_db=12), "1234567")[
        0
    ] == pytest.approx(124.250)


@pytest.mark.parametrize("level", [60, 94, 110])
def test_known_synthetic_pressure_levels_through_complete_dsp(level):
    cal = parse_calibration(FILE)
    offset, _ = umik_file_offset(cal, PROFILE, "1234567")
    # Independent reference vector: this mic gives -30.250 RMS dBFS at 94 dB SPL.
    rms_dbfs = -30.250 + (level - 94)
    samples = (
        np.sqrt(2)
        * 10 ** (rms_dbfs / 20)
        * np.sin(2 * np.pi * 1000 * np.arange(BLOCK) / SAMPLE_RATE)
    )
    assert db(float(np.mean(samples**2))) == pytest.approx(rms_dbfs, abs=1e-10)
    processor = Processor(offset=offset, calibration=cal)
    for _ in range(100):
        levels, spectrum = processor.process(samples)
    processor.reset_peak()
    levels, _ = processor.process(samples)
    assert levels.lasDb == pytest.approx(level, abs=0.03)
    assert levels.laeq1Db == pytest.approx(level, abs=0.03)
    assert levels.laeq10Db == pytest.approx(level, abs=0.03)
    assert levels.lcpeakDb == pytest.approx(level + 3.0103, abs=0.05)
    assert spectrum.unit == "dB SPL"


def test_sensitivity_sign_and_full_scale_convention():
    cal = parse_calibration(FILE.replace("-0.250", "4.0"))
    assert umik_file_offset(cal, PROFILE, "1234567")[0] == 120
    assert db(0.5) == pytest.approx(-3.0102999566)


def test_profile_and_serial_gates():
    cal = parse_calibration(FILE)
    assert umik_file_offset(cal, PROFILE)[0] is None
    assert umik_file_offset(cal, PROFILE, "wrong")[0] is None
    assert umik_file_offset(cal, replace(PROFILE, usb_serial="123-4567"))[0] is not None
    assert umik_file_offset(cal, replace(PROFILE, usb_serial="9999999"), "1234567")[0] is None
    assert umik_file_offset(cal, replace(PROFILE, direct_pcm=False), "1234567")[0] is None
    assert umik_file_offset(cal, replace(PROFILE, digital_gain_db=None), "1234567")[0] is None
    assert umik_file_offset(parse_calibration("20 0\n20000 0"), PROFILE, "1234567")[0] is None


def test_actual_mixer_controls_identify_direct_path():
    selected = {
        "usbVendor": "2752",
        "usbProduct": "0007",
        "name": "Umik-1  Gain: 18dB: USB Audio (hw:1,0)",
        "alsaCard": 1,
        "usbSerial": "000-0000",
        "binding": "usb-port",
    }
    controls = (
        "numid=2,iface=MIXER,name='Mic Capture Switch'\n"
        " ; type=BOOLEAN,access=rw------,values=1\n : values=on\n"
        "numid=1,iface=PCM,name='Capture Channel Map'\n"
        " ; type=INTEGER,access=r--v-R--,values=2\n : values=3,4"
    )
    with patch("spl_dashboard.capture.subprocess.run", return_value=MagicMock(stdout=controls)):
        info = inspect_calibration_input(selected)
        assert info.direct_pcm and info.digital_gain_db == 0
        assert info.analog_gain_db == 18
    for invalid in [
        controls.replace("values=on", "values=off"),
        controls + "\nnumid=3,iface=MIXER,name='Mic Capture Volume'\n ; type=INTEGER",
    ]:
        with patch("spl_dashboard.capture.subprocess.run", return_value=MagicMock(stdout=invalid)):
            assert not inspect_calibration_input(selected).direct_pcm


def test_runtime_file_method_manual_override_and_disabled(tmp_path):
    rt = Runtime(tmp_path)
    rt.input_calibration = PROFILE
    rt.settings = Settings(
        mode="device", device="selected", calibrationText=FILE, confirmedMicSerial="1234567"
    )
    rt.build_processor()
    assert rt.frame.status.calibrated
    assert rt.frame.status.validationPending  # File calibration is not field validation.
    assert rt.frame.diagnostics.calibrationMethod == "umik-file"
    assert rt.frame.diagnostics.referenceOffsetDb == pytest.approx(124.250, abs=0.03)
    rt.settings = rt.settings.model_copy(update={"calibrationMode": "off"})
    rt.build_processor()
    assert rt.processor.offset is None
    assert rt.frame.status.warmupSeconds == 0
    rt.settings = Settings(
        mode="device",
        device="selected",
        calibrationText=FILE,
        referenceDb=94,
        referenceRmsDbfs=-25,
        referenceNote="Test reference",
    )
    rt.build_processor()
    assert rt.frame.diagnostics.calibrationMethod == "reference"
    assert rt.processor.offset == pytest.approx(119, abs=0.03)
    rt.store.close()


def test_auto_calibration_recovers_durable_peak_after_input_is_identified(tmp_path):
    async def check():
        rt = Runtime(tmp_path)
        rt.settings = Settings(
            mode="device", device="selected", calibrationText=FILE, confirmedMicSerial="1234567"
        )
        rt.store.save_settings(rt.settings)
        rt.input_calibration = PROFILE
        rt.start_event("File-cal event")
        from spl_dashboard.models import Levels

        rt.frame.measured = Levels(lcpeakDb=110)
        rt.store.append(rt.frame)
        rt.store.close()
        restarted = Runtime(tmp_path)
        with patch.object(restarted, "capture_loop", new=asyncio.Event().wait):
            await restarted.start()
            assert restarted.processor.offset is None
            restarted.input_calibration = PROFILE
            restarted.build_processor(preserve_peak=True)
            recovered = 10 * np.log10(restarted.processor.peak) + restarted.processor.offset
            assert recovered == pytest.approx(110)
            await restarted.close()

    asyncio.run(check())
