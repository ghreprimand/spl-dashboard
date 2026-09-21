"""Manual sensitivity mode and guided raw-RMS reference capture."""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from spl_dashboard.main import create_app
from spl_dashboard.models import Settings
from spl_dashboard.runtime import Runtime

HEADERS = {"X-SPL-Client": "dashboard"}


def test_manual_mode_applies_94db_sensitivity(tmp_path):
    rt = Runtime(tmp_path)
    rt.settings = Settings(
        mode="device",
        device="selected",
        calibrationMode="manual",
        manualDbfsAt94=-30.0,
        referenceNote="Focusrite Solo, macOS input 75%, no boost",
    )
    rt.build_processor()
    assert rt.frame.status.calibrated
    assert rt.frame.diagnostics.calibrationMethod == "manual"
    # offset = 94 - (-30) = 124 dB.
    assert rt.processor.offset == pytest.approx(124.0)
    rt.store.close()


def test_manual_mode_adds_field_trim(tmp_path):
    rt = Runtime(tmp_path)
    rt.settings = Settings(
        mode="device",
        device="selected",
        calibrationMode="manual",
        manualDbfsAt94=-30.0,
        fieldTrimDb=2.0,
        referenceNote="interface note",
    )
    rt.build_processor()
    assert rt.processor.offset == pytest.approx(126.0)
    rt.store.close()


def test_manual_mode_requires_value_and_note():
    with pytest.raises(ValueError):
        Settings(mode="device", device="x", calibrationMode="manual")
    with pytest.raises(ValueError):
        Settings(mode="device", device="x", calibrationMode="manual", manualDbfsAt94=-30.0)


def test_reference_capture_rejects_the_demonstration_signal(tmp_path):
    async def check() -> None:
        rt = Runtime(tmp_path)  # defaults to demo mode
        with pytest.raises(ValueError, match="real input"):
            await rt.capture_reference_rms(seconds=0.1)
        rt.store.close()

    asyncio.run(check())


def test_reference_capture_averages_raw_energy(tmp_path):
    async def check() -> None:
        rt = Runtime(tmp_path)
        rt.settings = rt.settings.model_copy(update={"mode": "device", "device": "selected"})
        rt.frame.status.connected = True
        rt.frame.status.stale = False
        mean_square = 0.01  # -20 dBFS
        now = time.monotonic()
        for _ in range(60):
            rt.raw_energy.append((now, mean_square))
        result = await rt.capture_reference_rms(seconds=0.2)
        assert result["rmsDbfs"] == pytest.approx(-20.0, abs=0.05)
        assert result["seconds"] >= 0.2
        rt.store.close()

    asyncio.run(check())


def test_reference_capture_endpoint_returns_400_on_demo(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.post("/api/reference/capture", headers=HEADERS)
        assert response.status_code == 400
        assert "real input" in response.json()["detail"]
