export interface Levels {
  lasMaxDb?: number | null;
  lasDb: number | null;
  laeq1Db: number | null;
  laeq10Db: number | null;
  lcpeakDb: number | null;
}
export interface SpectrumBands {
  fraction: number;
  centresHz: number[];
  edgesHz: number[];
  levelsDb: (number | null)[];
  smoothedLevelsDb: (number | null)[];
  windowSeconds: number;
  minWindowSeconds?: number;
  windowSecondsByBand?: number[];
  ready: boolean;
}
export interface Spectrum {
  updateHz?: number;
  analysisId?: string;
  sequence?: number;
  bands?: SpectrumBands[];
  traceCentresHz?: number[];
  traceLevelsDb?: (number | null)[];
  centresHz: number[];
  levelsDb: (number | null)[];
  unit: "dBFS" | "dB SPL";
  method: string;
}
export interface TelemetryFrame {
  readingLocation?: {
    mappingId?: string | null;
    audience: boolean;
    name: string;
    offsetDb: number | null;
    mappedAt: string | null;
  };
  schemaVersion: 2;
  timestamp: string;
  sequence: number;
  source: "demo" | "wav-unverified" | "umik-unverified";
  status: {
    connected: boolean;
    calibrated: boolean;
    validationPending: boolean;
    clipping: boolean;
    stale: boolean;
    message: string;
    overruns: number;
    gapCount: number;
    clipSeconds: number;
    warmupSeconds: number;
    loggingError: string | null;
  };
  diagnostics: {
    rmsDbfs: number | null;
    peakDbfs: number | null;
    sampleRate: number;
    device: string;
    calibrationHash: string | null;
    calibrationSerial: string | null;
    sensitivityFactor: number | null;
    framesProcessed: number;
    inputAgeSeconds: number | null;
    referenceOffsetDb: number | null;
    calibrationMethod?: "none" | "demo" | "umik-file" | "reference";
    calibrationReason?: string;
    calibrationModel?: string | null;
    analogGainDb?: number | null;
    digitalGainDb?: number | null;
    deviceBinding?: string;
  };
  measured: Levels | null;
  estimatedAudience: Levels | null;
  spectrum: Spectrum;
  alarms: string[];
  eventId: string | null;
  peakHold: string;
}
export interface Settings {
  audienceDisplay?: boolean | null;
  mode: "demo" | "device" | "wav";
  device: string;
  channel: number;
  sampleRate: 48000;
  wavPath: string;
  calibrationText: string;
  calibrationMode: "auto" | "reference" | "off";
  confirmedMicSerial: string;
  referenceDb: number | null;
  referenceRmsDbfs: number | null;
  referenceNote: string;
  fieldTrimDb: number;
  lasThreshold: number | null;
  leqThreshold: number | null;
  peakThreshold: number | null;
  audienceMappingNote?: string;
  venueName: string;
  audienceOffsetDb: number | null;
}
export interface EventInfo {
  id: string;
  name: string;
  started: string;
  stopped: string | null;
  annotations?: { timestamp: string; text: string }[];
}
export interface Device {
  id: string;
  name: string;
  channels: number;
  serialBound: boolean;
  binding?: string;
  usbSerial?: string | null;
}

export interface SavedMapping {
  id: string;
  name: string;
  offsetDb: number;
  mappedAt: string | null;
}

export interface Addresses {
  port: number;
  localAdmin: string;
  localDisplay: string;
  lan: { host: string; admin: string; display: string }[];
  note: string;
}
