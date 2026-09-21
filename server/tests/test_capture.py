import wave
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from spl_dashboard.capture import CAPTURE_BLOCK as BLOCK
from spl_dashboard.capture import DeviceInput, WavInput


@pytest.mark.parametrize("width", [2, 3, 4])
def test_wav_pcm_formats_and_eof(tmp_path, width):
    path = tmp_path / "fixture.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(width)
        out.setframerate(48000)
        values = [-(2 ** (8 * width - 2)), 0, 2 ** (8 * width - 2)] * (BLOCK // 3)
        out.writeframes(b"".join(v.to_bytes(width, "little", signed=True) for v in values))
    source = WavInput(path, 0)
    block = source.read()
    assert block.samples[:3].tolist() == [-0.5, 0, 0.5]
    assert source.read() is None
    source.close()


def test_bad_wav_rate_rejected(tmp_path):
    path = tmp_path / "fixture.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(44100)
        out.writeframes(np.zeros(100, dtype="<i2").tobytes())
    with pytest.raises(ValueError, match="48 kHz"):
        WavInput(path, 0)


@patch.dict("sys.modules", {"sounddevice": MagicMock()})
def test_no_device_fallback_or_ambiguous_match():
    # Do not open hardware during tests.
    with patch("spl_dashboard.capture.devices", return_value=[]):
        with pytest.raises(ValueError, match="missing or ambiguous"):
            DeviceInput("not-default", 0)
    with patch("spl_dashboard.capture.devices", return_value=[{"id": "same"}, {"id": "same"}]):
        with pytest.raises(ValueError, match="missing or ambiguous"):
            DeviceInput("same", 0)


def test_portaudio_refresh_never_terminates_a_running_stream():
    from spl_dashboard import capture

    sd = MagicMock()
    sd.query_devices.return_value = []
    sd.query_hostapis.return_value = []
    with (
        patch.dict("sys.modules", {"sounddevice": sd}),
        patch.object(capture, "_active_streams", 1),
    ):
        capture.devices()
        sd._terminate.assert_not_called()
    with (
        patch.dict("sys.modules", {"sounddevice": sd}),
        patch.object(capture, "_active_streams", 0),
    ):
        capture.devices()
        sd._terminate.assert_called_once()
        sd._initialize.assert_called_once()
