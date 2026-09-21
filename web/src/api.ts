import type { SpectrumBands, TelemetryFrame } from "./types";

export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-SPL-Client": "dashboard",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return response.json() as Promise<T>;
}

export function validFrame(value: unknown): value is TelemetryFrame {
  if (!value || typeof value !== "object") return false;
  const f = value as TelemetryFrame;
  const finite = (v: unknown) =>
    v === null || (typeof v === "number" && Number.isFinite(v));
  const levels = (v: TelemetryFrame["measured"]) =>
    v === null ||
    (v &&
      (v.lasMaxDb === undefined || finite(v.lasMaxDb)) &&
      ["lasDb", "laeq1Db", "laeq10Db", "lcpeakDb"].every((k) =>
        finite(v[k as keyof typeof v]),
      ));
  const validBands = (b: SpectrumBands) =>
    !!b &&
    [3, 6, 12].includes(b.fraction) &&
    typeof b.ready === "boolean" &&
    [1, 2].includes(b.windowSeconds) &&
    Array.isArray(b.centresHz) &&
    b.centresHz.length > 0 &&
    b.centresHz.length <= 150 &&
    b.centresHz.every(
      (v, i) =>
        Number.isFinite(v) && v > 0 && (i === 0 || v > b.centresHz[i - 1]),
    ) &&
    Array.isArray(b.edgesHz) &&
    b.edgesHz.length === b.centresHz.length + 1 &&
    b.edgesHz.every(
      (v, i) =>
        Number.isFinite(v) && v > 0 && (i === 0 || v > b.edgesHz[i - 1]),
    ) &&
    Array.isArray(b.levelsDb) &&
    Array.isArray(b.smoothedLevelsDb) &&
    b.levelsDb.length === (b.ready ? b.centresHz.length : 0) &&
    b.smoothedLevelsDb.length === b.levelsDb.length &&
    b.levelsDb.every(finite) &&
    b.smoothedLevelsDb.every(finite);
  return (
    (f.readingLocation === undefined ||
      (!!f.readingLocation &&
        typeof f.readingLocation.audience === "boolean" &&
        typeof f.readingLocation.name === "string" &&
        finite(f.readingLocation.offsetDb) &&
        (f.readingLocation.mappedAt === null ||
          typeof f.readingLocation.mappedAt === "string"))) &&
    f.schemaVersion === 2 &&
    Number.isFinite(f.sequence) &&
    typeof f.timestamp === "string" &&
    Number.isFinite(Date.parse(f.timestamp)) &&
    ["demo", "wav-unverified", "umik-unverified"].includes(f.source) &&
    !!f.status &&
    ["connected", "calibrated", "validationPending", "clipping", "stale"].every(
      (k) => typeof f.status[k as keyof typeof f.status] === "boolean",
    ) &&
    typeof f.status.message === "string" &&
    Number.isFinite(f.status.warmupSeconds) &&
    !!f.diagnostics &&
    finite(f.diagnostics.rmsDbfs) &&
    finite(f.diagnostics.peakDbfs) &&
    !!f.spectrum &&
    ["dBFS", "dB SPL"].includes(f.spectrum.unit) &&
    (f.spectrum.bands === undefined ||
      (Array.isArray(f.spectrum.bands) &&
        f.spectrum.bands.length <= 3 &&
        f.spectrum.bands.every(validBands))) &&
    Array.isArray(f.spectrum.centresHz) &&
    Array.isArray(f.spectrum.levelsDb) &&
    f.spectrum.centresHz.length === f.spectrum.levelsDb.length &&
    f.spectrum.centresHz.length <= 100 &&
    f.spectrum.levelsDb.every(finite) &&
    Array.isArray(f.alarms) &&
    f.alarms.every((a) => typeof a === "string") &&
    !!levels(f.measured) &&
    !!levels(f.estimatedAudience)
  );
}
