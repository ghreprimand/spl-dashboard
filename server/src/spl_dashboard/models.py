from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Settings(Model):
    mode: Literal["demo", "device", "wav"] = "demo"
    device: str = ""
    channel: int = Field(default=0, ge=0, le=31)
    sampleRate: Literal[48000] = 48000
    wavPath: str = ""
    calibrationText: str = Field(default="", max_length=200000)
    calibrationMode: Literal["auto", "reference", "off", "manual"] = "auto"
    confirmedMicSerial: str = Field(default="", max_length=40)
    referenceDb: float | None = Field(default=None, ge=40, le=140)
    referenceRmsDbfs: float | None = Field(default=None, ge=-120, le=0)
    referenceNote: str = Field(default="", max_length=500)
    manualDbfsAt94: float | None = Field(default=None, ge=-120, le=0)
    fieldTrimDb: float = Field(default=0, ge=-20, le=20)
    lasThreshold: float | None = Field(default=None, ge=40, le=140)
    leqThreshold: float | None = Field(default=None, ge=40, le=140)
    peakThreshold: float | None = Field(default=None, ge=40, le=160)
    audienceDisplay: bool | None = None  # None migrates existing mapped installations.
    audienceMappingNote: str = Field(default="", max_length=4000)
    venueName: str = Field(default="", max_length=120)
    audienceOffsetDb: float | None = Field(default=None, ge=-30, le=30)

    @model_validator(mode="after")
    def reference_pair(self) -> "Settings":
        if (self.referenceDb is None) != (self.referenceRmsDbfs is None):
            raise ValueError("Both known SPL and observed RMS dBFS are required")
        if self.calibrationMode == "auto" and self.referenceDb is not None:
            self.calibrationMode = "reference"  # Preserve existing explicit-reference settings.
        if self.referenceDb is not None and not self.referenceNote.strip():
            raise ValueError("Record reference equipment and input gain in the reference note")
        if self.calibrationMode == "manual":
            if self.manualDbfsAt94 is None:
                raise ValueError("Enter the raw RMS dBFS this microphone produces at 94 dB SPL")
            if not self.referenceNote.strip():
                raise ValueError("Record the input interface and OS input gain in the note")
        if self.audienceOffsetDb is not None and not self.venueName.strip():
            raise ValueError("Audience correction requires a named venue profile")
        if self.mode == "device" and not self.device:
            raise ValueError("Select an explicit input device")
        if self.mode == "wav" and not self.wavPath:
            raise ValueError("Provide a local WAV path on the appliance")
        return self


class Levels(Model):
    lasMaxDb: float | None = None
    lasDb: float | None = None
    laeq1Db: float | None = None
    laeq10Db: float | None = None
    lcpeakDb: float | None = None


class Status(Model):
    connected: bool = False
    calibrated: bool = False
    validationPending: bool = True
    clipping: bool = False
    stale: bool = True
    message: str = "Waiting for input"
    overruns: int = 0
    gapCount: int = 0
    clipSeconds: float = 0
    warmupSeconds: float = 600
    loggingError: str | None = None


class Diagnostics(Model):
    rmsDbfs: float | None = None
    peakDbfs: float | None = None
    sampleRate: int = 48000
    device: str = ""
    calibrationHash: str | None = None
    calibrationSerial: str | None = None
    sensitivityFactor: float | None = None
    framesProcessed: int = 0
    inputAgeSeconds: float | None = None
    referenceOffsetDb: float | None = None
    calibrationMethod: Literal["none", "demo", "umik-file", "reference", "manual"] = "none"
    calibrationReason: str = "No absolute calibration"
    calibrationModel: str | None = None
    analogGainDb: float | None = None
    digitalGainDb: float | None = None
    deviceBinding: str = "name"


class SpectrumBands(Model):
    fraction: int
    centresHz: list[float]
    edgesHz: list[float]
    levelsDb: list[float | None]
    smoothedLevelsDb: list[float | None]
    windowSeconds: float
    minWindowSeconds: float = 0.1
    windowSecondsByBand: list[float] = Field(default_factory=list)
    ready: bool


class Spectrum(Model):
    updateHz: int = 10
    analysisId: str = ""
    sequence: int = 0
    bands: list[SpectrumBands] = Field(default_factory=list)
    traceCentresHz: list[float] = Field(default_factory=list)
    traceLevelsDb: list[float | None] = Field(default_factory=list)
    centresHz: list[float] = Field(default_factory=list)
    levelsDb: list[float | None] = Field(default_factory=list)
    unit: Literal["dBFS", "dB SPL"] = "dBFS"
    method: str = "1 s Hann FFT band energy; unweighted"


class ReadingLocation(Model):
    mappingId: str | None = None
    audience: bool = False
    name: str = ""
    offsetDb: float | None = None
    mappedAt: str | None = None


class ReadingLocationRequest(Model):
    audience: bool


class TelemetryFrame(Model):
    readingLocation: ReadingLocation = Field(default_factory=ReadingLocation)
    schemaVersion: Literal[2] = 2
    timestamp: str
    sequence: int = 0
    source: Literal["demo", "wav-unverified", "umik-unverified"] = "demo"
    status: Status = Field(default_factory=Status)
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)
    measured: Levels | None = None
    estimatedAudience: Levels | None = None
    spectrum: Spectrum = Field(default_factory=Spectrum)
    alarms: list[str] = Field(default_factory=list)
    eventId: str | None = None
    peakHold: str = "since input start/reset"


class EventRequest(Model):
    name: str = Field(min_length=1, max_length=120)


class AnnotationRequest(Model):
    text: str = Field(min_length=1, max_length=1000)
