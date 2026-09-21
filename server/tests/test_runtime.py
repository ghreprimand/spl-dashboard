import asyncio
from unittest.mock import patch

import numpy as np
import pytest

from spl_dashboard.models import Levels, Settings
from spl_dashboard.runtime import Runtime


def test_gap_resets_windows_but_preserves_event_peak(tmp_path):
    rt = Runtime(tmp_path)
    rt.start_event("Gap test")
    rt.processor.peak = 0.5
    rt.processor.process(np.ones(4800) * 0.01)
    rt.frame.measured = Levels(lasDb=94, lcpeakDb=110)
    rt.gap("Unplugged")
    assert rt.frame.status.stale
    assert not rt.frame.status.connected
    assert rt.processor.peak >= 0.5
    assert len(rt.processor.ten_minutes.values) == 0
    assert rt.frame.status.gapCount == 1
    rt.gap("Still unplugged")
    assert rt.frame.status.gapCount == 1
    rt.store.close()


def test_reference_accounts_for_frequency_correction_at_1khz(tmp_path):
    rt = Runtime(tmp_path)
    rt.settings = Settings(
        mode="device",
        device="selected",
        referenceDb=94,
        referenceRmsDbfs=-30,
        referenceNote="1 kHz fixture, gain unchanged",
        calibrationText="20 6\n1000 6\n20000 6",
    )
    rt.build_processor()
    t = np.arange(4800) / 48000
    for _ in range(100):
        levels, _ = rt.processor.process(
            np.sqrt(2) * 10 ** (-30 / 20) * np.sin(2 * np.pi * 1000 * t)
        )
    assert levels.lasDb == pytest.approx(94, abs=0.03)
    assert rt.frame.source == "umik-unverified"
    assert rt.frame.status.validationPending
    rt.store.close()


def test_logging_failure_is_visible_and_recovers(tmp_path):
    async def check():
        rt = Runtime(tmp_path)
        rt.start_event("Disk test")
        with patch.object(rt.store, "append", side_effect=OSError("disk full")):
            task = asyncio.create_task(rt.heartbeat())
            await asyncio.sleep(0.02)
            assert "disk full" in rt.frame.status.loggingError
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        task = asyncio.create_task(rt.heartbeat())
        await asyncio.sleep(0.02)
        assert rt.frame.status.loggingError is None
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        rt.store.close()

    asyncio.run(check())


def test_venue_correction_never_replaces_raw_log(tmp_path):
    async def check():
        rt = Runtime(tmp_path)
        await rt.configure(Settings(venueName="Dance floor", audienceOffsetDb=3))
        rt.start_event("Mapping")
        rt.heartbeat_task = asyncio.create_task(rt.heartbeat())
        await asyncio.sleep(0.15)
        assert rt.frame.estimatedAudience.lasDb - rt.frame.measured.lasDb == pytest.approx(3)
        assert rt.frame.estimatedAudience.lcpeakDb is None
        rt.store.append(rt.frame)
        saved = rt.store.history(rt.frame.eventId)[-1]
        assert saved["measured"]["lasDb"] == rt.frame.measured.lasDb
        assert saved["estimatedAudience"]["lasDb"] == rt.frame.estimatedAudience.lasDb
        await rt.close()

    asyncio.run(check())


def test_clipping_and_eof_are_visible(tmp_path):
    import wave

    async def check():
        rt = Runtime(tmp_path)
        path = tmp_path / "fixtures" / "clip.wav"
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(48000)
            out.writeframes(np.full(4800, 32767, dtype="<i2").tobytes())
        await rt.configure(Settings(mode="wav", wavPath="clip.wav"))
        await asyncio.sleep(0.02)
        assert rt.frame.status.clipping
        assert rt.frame.status.clipSeconds == pytest.approx(0.1)
        assert rt.frame.measured is None
        await asyncio.sleep(0.12)
        assert rt.frame.status.stale
        assert "REPLAY ENDED" in rt.frame.status.message
        assert rt.frame.status.clipSeconds == pytest.approx(0.1)
        await rt.close()

    asyncio.run(check())


def test_reset_peak_without_recording(tmp_path):
    rt = Runtime(tmp_path)
    rt.processor.peak = 0.5
    rt.frame.measured = Levels(lcpeakDb=127)
    rt.reset_peak()
    assert rt.processor.peak == 0
    assert rt.frame.measured.lcpeakDb is None
    assert rt.store.current() is None
    rt.store.close()


def test_maximum_survives_gap_and_resets_independently(tmp_path):
    rt = Runtime(tmp_path)
    rt.processor.max_slow_db = 95.0
    rt.processor.peak = 0.5
    rt.gap("disconnect")
    assert rt.processor.max_slow_db == 95
    rt.frame.measured = Levels(lasMaxDb=95, lcpeakDb=110)
    rt.reset_maximum()
    assert rt.processor.max_slow_db is None
    assert rt.frame.measured.lasMaxDb is None
    assert rt.frame.measured.lcpeakDb == 110
    assert rt.processor.peak == 0.5
    rt.store.close()


def test_mapping_captures_fresh_energy_and_rejects_gaps(tmp_path, monkeypatch):
    rt = Runtime(tmp_path)
    rt.settings.mode = "device"
    rt.frame.status.connected = True
    rt.frame.status.stale = False
    rt.processor.offset = 100
    for _ in range(300):
        rt.processor.minute.add(0.0001)
    rt.processor.blocks = 300

    async def advance(_):
        rt.processor.blocks += 1
        rt.processor.minute.add(0.01)

    monkeypatch.setattr("spl_dashboard.runtime.asyncio.sleep", advance)
    result = asyncio.run(rt.capture_mapping_level())
    assert result["levelDb"] == pytest.approx(80)
    assert result["seconds"] == 30

    async def disconnect(_):
        rt.frame.status.connected = False

    monkeypatch.setattr("spl_dashboard.runtime.asyncio.sleep", disconnect)
    with pytest.raises(ValueError, match="disconnected"):
        asyncio.run(rt.capture_mapping_level())
    rt.store.close()
