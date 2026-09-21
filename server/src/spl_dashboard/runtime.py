import asyncio
import contextlib
import json
import logging
import time
from collections import deque
from pathlib import Path
from typing import Literal

import numpy as np
from scipy import signal

from .calibration import InputCalibration, parse_calibration, umik_file_offset
from .capture import CAPTURE_BLOCK, DemoInput, DeviceInput, WavInput
from .dsp import SAMPLE_RATE, Processor, db
from .models import Diagnostics, Levels, ReadingLocation, Settings, TelemetryFrame
from .storage import Store, mapping_id, utcnow

logger = logging.getLogger(__name__)


class Runtime:
    def __init__(self, directory: Path):
        self.directory = directory
        (directory / "fixtures").mkdir(parents=True, exist_ok=True)
        self.store = Store(directory / "events.sqlite3")
        self.settings = self.store.settings()
        self.frame = TelemetryFrame(timestamp=utcnow())
        self.processor = Processor()
        self.input_calibration = InputCalibration()
        self.pending_peak_db: float | None = None
        self.capture_task: asyncio.Task[None] | None = None
        self.heartbeat_task: asyncio.Task[None] | None = None
        self.last_input: float | None = None
        self.last_sequence = 0
        self.clip_until = 0.0
        self.gap_active = False
        # Recent raw block energies (monotonic time, mean square) for reference capture.
        self.raw_energy: deque[tuple[float, float]] = deque(maxlen=200)
        self.config_lock = asyncio.Lock()
        self.build_processor()

    def build_processor(self, preserve_peak: bool = False) -> None:
        settings = self.settings
        self.update_reading_location()
        calibration = parse_calibration(settings.calibrationText)
        offset = None
        method: Literal["none", "demo", "umik-file", "reference", "manual"] = "none"
        reason = "Absolute calibration disabled"
        if settings.mode == "demo":
            offset, method, reason = 128.0, "demo", "DEMO — generated signal"
        elif settings.calibrationMode == "manual" and settings.manualDbfsAt94 is not None:
            offset = 94.0 - settings.manualDbfsAt94
            method, reason = "manual", "Calibrated to the entered 94 dB SPL sensitivity"
            offset += settings.fieldTrimDb
            if calibration:
                _, response = signal.freqz(
                    calibration.fir(SAMPLE_RATE), worN=[1000], fs=SAMPLE_RATE
                )
                offset -= float(20 * np.log10(abs(response[0])))
        elif settings.calibrationMode not in ("off", "manual"):
            if settings.referenceDb is not None and settings.referenceRmsDbfs is not None:
                offset = settings.referenceDb - settings.referenceRmsDbfs
                method, reason = "reference", "Calibrated to the recorded acoustic reference"
            elif settings.calibrationMode == "auto" and settings.mode == "device":
                offset, reason = umik_file_offset(
                    calibration, self.input_calibration, settings.confirmedMicSerial
                )
                if offset is not None:
                    method = "umik-file"
            else:
                reason = "Enter both the known reference level and observed raw RMS dBFS"
            if offset is not None:
                offset += settings.fieldTrimDb
                if calibration:
                    _, response = signal.freqz(
                        calibration.fir(SAMPLE_RATE), worN=[1000], fs=SAMPLE_RATE
                    )
                    offset -= float(20 * np.log10(abs(response[0])))
        max_slow = self.processor.max_slow_db if preserve_peak else None
        peak = self.processor.peak if preserve_peak else 0.0
        old_offset = self.processor.offset
        if peak and old_offset is not None and offset is not None:
            peak *= 10 ** ((old_offset - offset) / 10)
        self.processor = Processor(calibration=calibration, offset=offset)
        self.processor.max_slow_db = max_slow
        self.processor.peak = peak
        if self.pending_peak_db is not None and offset is not None:
            self.processor.peak = max(
                self.processor.peak, 10 ** ((self.pending_peak_db - offset) / 10)
            )
            self.pending_peak_db = None
        self.frame.source = {"demo": "demo", "device": "umik-unverified", "wav": "wav-unverified"}[
            settings.mode
        ]  # type: ignore[assignment]
        self.frame.status.calibrated = method in ("umik-file", "reference", "manual")
        self.frame.status.warmupSeconds = 600 if offset is not None else 0
        self.frame.diagnostics = Diagnostics(
            device=settings.device if settings.mode == "device" else settings.mode,
            calibrationHash=calibration.digest if calibration else None,
            calibrationSerial=calibration.serial if calibration else None,
            sensitivityFactor=calibration.sensitivity if calibration else None,
            referenceOffsetDb=offset,
            calibrationMethod=method,
            calibrationReason=reason,
            calibrationModel="umik1-direct-pcm-v1" if method == "umik-file" else None,
            analogGainDb=self.input_calibration.analog_gain_db,
            digitalGainDb=self.input_calibration.digital_gain_db,
            deviceBinding=self.input_calibration.binding,
        )

    def wav_path(self, name: str) -> Path:
        root = (self.directory / "fixtures").resolve()
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() != ".wav":
            raise ValueError(
                "WAV must be an existing .wav file inside the appliance fixtures directory"
            )
        return path

    async def start(self) -> None:
        current = self.store.current()
        if current:
            history = self.store.history(current["id"], 1)
            if history:
                previous = history[-1]
                measured = previous.get("measured") or {}
                self.processor.max_slow_db = measured.get("lasMaxDb")
                peak = measured.get("lcpeakDb")
                if peak is not None:
                    if self.processor.offset is not None:
                        self.processor.peak = 10 ** ((peak - self.processor.offset) / 10)
                    else:
                        self.pending_peak_db = peak
                self.frame.status.gapCount = previous["status"]["gapCount"] + 1
            self.store.annotate(
                "Service restarted: input gap; averaging windows restarted; "
                "peak restored from last durable record."
            )
            self.frame.peakHold = "event/reset; gaps present"
        self.capture_task = asyncio.create_task(self.capture_loop())
        self.heartbeat_task = asyncio.create_task(self.heartbeat())

    async def close(self) -> None:
        for task in (self.capture_task, self.heartbeat_task):
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self.store.close()

    def update_reading_location(self) -> None:
        settings = self.settings
        mapped_at = None
        try:
            note = json.loads(settings.audienceMappingNote)
            if isinstance(note, dict) and isinstance(note.get("date"), str):
                mapped_at = note["date"]
        except (ValueError, TypeError):
            pass
        self.frame.readingLocation = ReadingLocation(
            mappingId=mapping_id(settings),
            audience=(
                settings.audienceDisplay
                if settings.audienceDisplay is not None
                else settings.audienceOffsetDb is not None
            ),
            name=settings.venueName,
            offsetDb=settings.audienceOffsetDb,
            mappedAt=mapped_at,
        )

    async def set_reading_location(self, audience: bool) -> None:
        async with self.config_lock:
            if audience and self.settings.audienceOffsetDb is None:
                raise ValueError("Apply an audience mapping first")
            updated = self.settings.model_copy(update={"audienceDisplay": audience})
            self.store.save_settings(updated)
            self.settings = updated
            self.update_reading_location()

    async def configure(
        self, settings: Settings | None, mapping: str | None = None, *, clear_mapping: bool = False
    ) -> None:
        async with self.config_lock:
            if clear_mapping:
                settings = self.settings.model_copy(
                    update={
                        "venueName": "",
                        "audienceOffsetDb": None,
                        "audienceMappingNote": "",
                        "audienceDisplay": False,
                    }
                )
            if mapping is not None:
                settings = Settings.model_validate(
                    {
                        **self.settings.model_dump(),
                        **self.store.mapping(mapping),
                        "audienceDisplay": True,
                    }
                )
            if settings is None:
                raise ValueError("Settings are required")
            if self.store.current():
                raise ValueError("Stop the event before changing input, calibration, or thresholds")
            parse_calibration(settings.calibrationText)
            if settings.mode == "wav":
                trial = WavInput(self.wav_path(settings.wavPath), settings.channel)
                trial.close()
            # Persist first; a write failure must not interrupt working capture.
            self.store.save_settings(settings)
            if self.capture_task:
                self.capture_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.capture_task
            sequence = self.frame.sequence
            self.settings = settings
            self.input_calibration = InputCalibration()
            self.pending_peak_db = None
            self.frame = TelemetryFrame(timestamp=utcnow(), sequence=sequence)
            self.build_processor()
            self.last_input = None
            self.last_sequence = 0
            self.gap_active = False
            self.capture_task = asyncio.create_task(self.capture_loop())

    def gap(self, message: str) -> None:
        self.frame.status.message = message
        self.frame.status.stale = True
        self.frame.status.connected = False
        if not self.gap_active:
            self.frame.status.gapCount += 1
            self.build_processor(preserve_peak=True)
            self.gap_active = True
            self.frame.peakHold = (
                "event/reset; gaps present" if self.store.current() else "input/reset; gaps present"
            )

    async def capture_loop(self) -> None:
        while True:
            source: DemoInput | DeviceInput | WavInput | None = None
            try:
                if self.settings.mode == "device":
                    source = DeviceInput(self.settings.device, self.settings.channel)
                    self.input_calibration = source.calibration_info
                    self.build_processor(preserve_peak=True)
                    self.frame.measured = None
                    self.frame.estimatedAudience = None
                elif self.settings.mode == "wav":
                    source = WavInput(self.wav_path(self.settings.wavPath), self.settings.channel)
                else:
                    source = DemoInput()
                self.last_sequence = 0
                deadline = time.monotonic()
                while True:
                    if isinstance(source, DeviceInput):
                        block = await asyncio.to_thread(source.read)
                    else:
                        await asyncio.sleep(max(0, deadline - time.monotonic()))
                        block = source.read()
                        deadline += CAPTURE_BLOCK / SAMPLE_RATE
                    if block is None:
                        if isinstance(source, WavInput):
                            self.gap("REPLAY ENDED — select input or restart replay")
                            return
                        if self.last_input is None or time.monotonic() - self.last_input > 2:
                            raise ValueError("MIC LOST — no input blocks; retrying selected device")
                        continue
                    if time.monotonic() - block.captured > 0.5:
                        self.gap("Input backlog discarded")
                        continue
                    if block.overflow or (
                        self.last_sequence and block.sequence != self.last_sequence + 1
                    ):
                        self.frame.status.overruns += 1
                        self.gap("AUDIO GAP — input buffers dropped")
                    self.last_sequence = block.sequence
                    self.last_input = block.captured
                    self.gap_active = False
                    measured, spectrum = self.processor.process(block.samples)
                    self.frame.measured = measured
                    offset = self.settings.audienceOffsetDb
                    if measured and offset is not None:
                        # A-only mapping; broadband offsets do not justify a C-peak estimate.
                        self.frame.estimatedAudience = Levels(
                            lasMaxDb=measured.lasMaxDb + offset
                            if measured.lasMaxDb is not None
                            else None,
                            lasDb=measured.lasDb + offset if measured.lasDb is not None else None,
                            laeq1Db=measured.laeq1Db + offset
                            if measured.laeq1Db is not None
                            else None,
                            laeq10Db=measured.laeq10Db + offset
                            if measured.laeq10Db is not None
                            else None,
                        )
                    else:
                        self.frame.estimatedAudience = None
                    self.frame.spectrum = spectrum
                    status = self.frame.status
                    peak = float(np.max(np.abs(block.samples)))
                    if peak >= 0.999:
                        self.clip_until = time.monotonic() + 1
                        status.clipSeconds += (
                            float(np.count_nonzero(abs(block.samples) >= 0.999)) / SAMPLE_RATE
                        )
                    status.clipping = time.monotonic() < self.clip_until
                    status.connected = True
                    status.stale = False
                    status.message = self.frame.diagnostics.calibrationReason
                    status.warmupSeconds = (
                        max(0, 600 - self.processor.blocks / 10)
                        if self.processor.offset is not None
                        else 0
                    )
                    diag = self.frame.diagnostics
                    mean_square = float(np.mean(block.samples**2))
                    diag.rmsDbfs = db(mean_square)
                    diag.peakDbfs = db(peak**2)
                    diag.framesProcessed += CAPTURE_BLOCK
                    self.raw_energy.append((block.captured, mean_square))
                    previous_alarms = self.frame.alarms
                    self.frame.alarms = []
                    if measured:
                        for value, threshold, label in [
                            (measured.lasDb, self.settings.lasThreshold, "LAS LIMIT"),
                            (measured.laeq10Db, self.settings.leqThreshold, "LAeq10 LIMIT"),
                            (measured.lcpeakDb, self.settings.peakThreshold, "LCpeak LIMIT"),
                        ]:
                            if value is not None and threshold is not None and value >= threshold:
                                self.frame.alarms.append(label)
                    if self.frame.alarms != previous_alarms and self.store.current():
                        try:
                            self.store.annotate(
                                "Threshold state: " + (", ".join(self.frame.alarms) or "clear")
                            )
                        except Exception as exc:
                            self.frame.status.loggingError = f"LOG FAILURE: {exc}"
                    self.frame.sequence += 1
                    self.frame.timestamp = utcnow()
                    await asyncio.sleep(0)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Input unavailable: %s", exc)
                self.gap(str(exc))
            finally:
                if source:
                    try:
                        source.close()
                    except Exception as exc:
                        logger.warning("Input cleanup failed: %s", exc)
            await asyncio.sleep(2)

    async def heartbeat(self) -> None:
        next_log = time.monotonic()
        while True:
            now = time.monotonic()
            age = now - self.last_input if self.last_input is not None else None
            if age is not None and age > 2 and not self.gap_active:
                self.gap("STALE — input stopped")
            self.frame.diagnostics.inputAgeSeconds = age
            self.frame.sequence += 1
            self.frame.timestamp = utcnow()
            current = self.store.current()
            self.frame.eventId = current["id"] if current else None
            if now >= next_log:
                next_log = now + 1
                try:
                    self.store.append(self.frame)
                    self.frame.status.loggingError = None
                except Exception as exc:
                    self.frame.status.loggingError = f"LOG FAILURE: {exc}"
                    logger.exception("Telemetry could not be persisted")
            await asyncio.sleep(0.1)

    def start_event(self, name: str) -> dict:
        event = self.store.start(name, self.settings)
        self.build_processor()
        self.frame.measured = None
        self.frame.estimatedAudience = None
        self.frame.eventId = event["id"]
        self.frame.peakHold = "since event start/reset"
        return event

    def reset_peak(self) -> None:
        if self.store.current():
            self.store.annotate("LCpeak reset by operator")
        self.processor.reset_peak()
        if self.frame.measured:
            self.frame.measured.lcpeakDb = None
        self.frame.peakHold = "since operator reset"
        self.frame.timestamp = utcnow()
        self.store.append(self.frame)

    def reset_maximum(self) -> None:
        if self.store.current():
            self.store.annotate("Maximum live level reset by operator")
        self.processor.max_slow_db = None
        if self.frame.measured:
            self.frame.measured.lasMaxDb = None
        self.frame.timestamp = utcnow()
        self.store.append(self.frame)

    async def capture_mapping_level(self) -> dict:
        """Thirty seconds of actual A-weighted energy, never an average of dB."""
        if self.store.current():
            raise ValueError("Stop event recording before audience mapping")
        if (
            not self.frame.status.connected
            or self.frame.status.stale
            or self.processor.offset is None
        ):
            raise ValueError("A connected calibrated input is required")
        if self.settings.mode != "device":
            raise ValueError("Audience mapping requires the physical microphone")
        processor = self.processor
        start = processor.blocks
        clips = self.frame.status.clipSeconds
        deadline = time.monotonic() + 40
        while processor.blocks - start < 300:
            if (
                self.processor is not processor
                or not self.frame.status.connected
                or self.frame.status.stale
            ):
                raise ValueError("Input changed or disconnected; repeat this capture")
            if self.frame.status.clipSeconds != clips:
                raise ValueError("Input clipped; reduce playback and repeat all mapping captures")
            if time.monotonic() > deadline:
                raise ValueError("Capture timed out; repeat this position")
            await asyncio.sleep(0.1)
        count = processor.blocks - start
        if self.processor is not processor or count > 600 or self.frame.status.clipSeconds != clips:
            raise ValueError("Input changed during capture; repeat this position")
        energy = float(np.mean(list(processor.minute.values)[-count:]))
        level = db(energy)
        if level is None or processor.offset is None:
            raise ValueError("No usable signal captured")
        return {
            "levelDb": level + processor.offset,
            "seconds": count / 10,
            "calibrationHash": self.frame.diagnostics.calibrationHash,
            "offsetDb": processor.offset,
            "device": self.settings.device,
        }

    async def capture_reference_rms(self, seconds: float = 5.0) -> dict:
        """Average raw RMS dBFS over a few seconds to fill the reference field.

        This measures the level of a steady reference source (an acoustic
        calibrator or a stable tone at a known SPL) in the app's own dBFS scale,
        so the operator does not have to read it from another application.
        """
        if self.store.current():
            raise ValueError("Stop event recording before capturing a reference")
        if self.settings.mode == "demo":
            raise ValueError("Reference capture needs a real input, not the demonstration signal")
        if not self.frame.status.connected or self.frame.status.stale:
            raise ValueError("A connected, live input is required")
        needed = max(1, round(seconds * 10))
        start = time.monotonic()
        clips = self.frame.status.clipSeconds
        gaps = self.frame.status.gapCount
        deadline = start + seconds + 10
        while time.monotonic() - start < seconds:
            if not self.frame.status.connected or self.frame.status.stale:
                raise ValueError("Input stopped during capture; repeat it")
            if self.frame.status.clipSeconds != clips:
                raise ValueError("Input clipped during capture; reduce the level and repeat it")
            if self.frame.status.gapCount != gaps:
                raise ValueError("Input gap during capture; repeat it")
            if time.monotonic() > deadline:
                raise ValueError("Capture timed out; repeat it")
            await asyncio.sleep(0.05)
        recent = list(self.raw_energy)[-needed:]
        if len(recent) < needed:
            raise ValueError("Not enough audio captured; repeat it")
        rms = db(float(np.mean([mean_square for _, mean_square in recent])))
        if rms is None:
            raise ValueError("Signal too quiet to measure; check the input and level")
        return {"rmsDbfs": round(rms, 2), "seconds": round(len(recent) / 10, 1)}
