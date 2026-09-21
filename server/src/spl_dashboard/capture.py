"""Bounded local capture. Audio never leaves this module's process."""

import re
import subprocess
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Full, Queue
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .calibration import InputCalibration, usable_serial
from .dsp import SAMPLE_RATE

CAPTURE_BLOCK = 4800

_portaudio_lock = threading.RLock()
_active_streams = 0


@dataclass
class AudioBlock:
    samples: NDArray[np.float64]
    captured: float
    sequence: int
    overflow: bool = False


def devices() -> list[dict[str, Any]]:
    """Refresh PortAudio only when no input stream is open; never interrupt capture."""
    import sounddevice as sd

    with _portaudio_lock:
        if not _active_streams:
            sd._terminate()
            sd._initialize()
        hosts = sd.query_hostapis()
        result = []
        for index, device in enumerate(sd.query_devices()):
            if device["max_input_channels"] < 1:
                continue
            name = device["name"]
            host = hosts[device["hostapi"]]["name"]
            stable_name = re.sub(r"\s*\(hw:\d+,\d+\)", "", name)
            identity = f"portaudio:{host}:{stable_name}"
            binding, serial, vendor, product, card_index = "name", None, None, None, None
            match = re.search(r"hw:(\d+),(\d+)", name)
            if host == "ALSA" and match:
                card_index = int(match[1])
                card = Path(f"/sys/class/sound/card{card_index}/device").resolve()
                for parent in [card, *list(card.parents)[:4]]:
                    if (parent / "idVendor").is_file() and (parent / "idProduct").is_file():
                        vendor = (parent / "idVendor").read_text().strip()
                        product = (parent / "idProduct").read_text().strip()
                        serial_path = parent / "serial"
                        serial = serial_path.read_text().strip() if serial_path.is_file() else None
                        if usable_serial(serial):
                            identity = f"usb:{vendor}:{product}:{serial}:pcm{match[2]}"
                            binding = "serial"
                        else:
                            # A placeholder serial identifies a model, not a physical microphone.
                            controller = next(
                                (
                                    p.name
                                    for p in parent.parents
                                    if re.fullmatch(
                                        r"[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", p.name
                                    )
                                ),
                                "unknown",
                            )
                            port = parent.name.partition("-")[2]
                            identity = (
                                f"usb-port:{vendor}:{product}:{controller}/{port}:pcm{match[2]}"
                            )
                            binding = "usb-port"
                        break
            result.append(
                {
                    "id": identity,
                    "index": index,
                    "name": name,
                    "channels": device["max_input_channels"],
                    "defaultSampleRate": device["default_samplerate"],
                    "serialBound": binding == "serial",
                    "binding": binding,
                    "usbSerial": serial,
                    "usbVendor": vendor,
                    "usbProduct": product,
                    "alsaCard": card_index,
                }
            )
        return result


def inspect_calibration_input(selected: dict[str, Any]) -> InputCalibration:
    """Recognize the legacy UMIK-1 direct ALSA path and verify its mixer controls."""
    common = {"usb_serial": selected.get("usbSerial"), "binding": selected.get("binding", "name")}
    gain_match = re.search(r"Umik-1\s+Gain:\s*(\d+)dB", selected["name"], re.I)
    if (selected.get("usbVendor"), selected.get("usbProduct")) != (
        "2752",
        "0007",
    ) or not gain_match:
        return InputCalibration(
            **common, reason="Automatic calibration needs a supported direct UMIK-1 input"
        )
    gain = float(gain_match[1])
    if gain not in (0, 6, 12, 18, 24, 30, 36) or selected.get("alsaCard") is None:
        return InputCalibration(**common, reason="UMIK analog gain could not be identified")
    try:
        mixer = subprocess.run(
            ["amixer", "-c", str(selected["alsaCard"]), "contents"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return InputCalibration(**common, reason="Cannot inspect ALSA gain; install alsa-utils")
    # This device generation exposes only a mute switch. Reject volume/unknown
    # controls rather than guessing their gain mapping or silently applying it.
    sections = [
        part
        for part in mixer.split("numid=")[1:]
        if not ("iface=PCM" in part and "name='Capture Channel Map'" in part)
    ]
    if not sections or any(
        "name='Mic Capture Switch'" not in part or "type=BOOLEAN" not in part for part in sections
    ):
        return InputCalibration(
            **common, reason="Unexpected input gain controls; use an acoustic reference"
        )
    if any(re.search(r": values=(?:off|0)(?:\s|,|$)", part) for part in sections):
        return InputCalibration(**common, reason="MIC MUTED — enable the ALSA capture switch")
    return InputCalibration(
        **common,
        supported_umik=True,
        direct_pcm=True,
        analog_gain_db=gain,
        digital_gain_db=0.0,
        reason="Direct ALSA PCM; no digital gain control",
    )


class DeviceInput:
    def __init__(self, identity: str, channel: int):
        import sounddevice as sd

        global _active_streams
        self.closed = False
        with _portaudio_lock:
            matches = [d for d in devices() if d["id"] == identity]
            if len(matches) != 1:
                raise ValueError("Selected device is missing or ambiguous; select a unique input")
            selected = matches[0]
            if channel >= selected["channels"]:
                raise ValueError("Selected channel does not exist")
            self.calibration_info = inspect_calibration_input(selected)
            self.queue: Queue[AudioBlock] = Queue(maxsize=8)
            self.dropped = 0
            self.sequence = 0
            self.stream = sd.InputStream(
                device=selected["index"],
                samplerate=SAMPLE_RATE,
                blocksize=CAPTURE_BLOCK,
                channels=channel + 1,
                dtype="float32",
                callback=self.callback(channel),
            )
            try:
                self.stream.start()
            except Exception:
                self.stream.close()
                raise
            _active_streams += 1

    def callback(self, channel: int) -> Any:
        def receive(data: Any, frames: int, timing: Any, status: Any) -> None:
            self.sequence += 1
            block = AudioBlock(
                np.asarray(data[:, channel], dtype=np.float64).copy(),
                time.monotonic(),
                self.sequence,
                bool(status),
            )
            try:
                self.queue.put_nowait(block)
            except Full:
                self.dropped += 1

        return receive

    def read(self) -> AudioBlock | None:
        try:
            return self.queue.get(timeout=0.25)
        except Empty:
            return None

    def close(self) -> None:
        global _active_streams
        with _portaudio_lock:
            if self.closed:
                return
            try:
                self.stream.stop()
            finally:
                try:
                    self.stream.close()
                finally:
                    _active_streams -= 1
                    self.closed = True


class WavInput:
    def __init__(self, path: Path, channel: int):
        self.file = wave.open(str(path), "rb")
        self.channel = channel
        self.sequence = 0
        if (
            self.file.getframerate() != SAMPLE_RATE
            or self.file.getsampwidth() not in (2, 3, 4)
            or self.file.getcomptype() != "NONE"
            or channel >= self.file.getnchannels()
        ):
            self.file.close()
            raise ValueError("WAV must be 48 kHz PCM 16/24/32-bit with the selected channel")

    def read(self) -> AudioBlock | None:
        raw = self.file.readframes(CAPTURE_BLOCK)
        width = self.file.getsampwidth()
        channels = self.file.getnchannels()
        if len(raw) != CAPTURE_BLOCK * width * channels:
            return None  # No zero padding and no silent loop across a discontinuity.
        if width == 3:
            triples = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
            integer = triples[:, 0] | (triples[:, 1] << 8) | (triples[:, 2] << 16)
            integer = (integer ^ 0x800000) - 0x800000
            samples = integer.astype(np.float64) / 8388608
        else:
            samples = np.frombuffer(raw, dtype=f"<i{width}").astype(np.float64)
            samples /= 2 ** (width * 8 - 1)
        self.sequence += 1
        return AudioBlock(
            samples.reshape(-1, channels)[:, self.channel], time.monotonic(), self.sequence
        )

    def close(self) -> None:
        self.file.close()


class DemoInput:
    def __init__(self) -> None:
        self.sequence = 0
        self.rng = np.random.default_rng(42)

    def read(self) -> AudioBlock:
        t = (np.arange(CAPTURE_BLOCK) + self.sequence * CAPTURE_BLOCK) / SAMPLE_RATE
        amplitude = 0.025 * 10 ** (3 * np.sin(t / 8) / 20)
        samples = amplitude * (np.sin(2 * np.pi * 1000 * t) + 0.6 * np.sin(2 * np.pi * 80 * t))
        samples += self.rng.normal(0, 0.002, CAPTURE_BLOCK)
        self.sequence += 1
        return AudioBlock(samples, time.monotonic(), self.sequence)

    def close(self) -> None:
        pass
