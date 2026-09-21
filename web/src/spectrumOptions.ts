export interface SpectrumOptions {
  fraction: 3 | 6 | 12;
  averaging: "live" | "stable";
  style: "steps" | "line";
  top: number;
  range: number;
}
export const spectrumDefaults: SpectrumOptions = {
  fraction: 6,
  averaging: "live",
  style: "steps",
  top: 100,
  range: 60,
};
export function normalizeSpectrumOptions(input: unknown): SpectrumOptions {
  const v = (
    input && typeof input === "object" ? input : {}
  ) as Partial<SpectrumOptions>;
  return {
    fraction: v.fraction === 3 || v.fraction === 12 ? v.fraction : 6,
    averaging: v.averaging === "stable" ? "stable" : "live",
    style: v.style === "line" ? "line" : "steps",
    top:
      typeof v.top === "number" && Number.isFinite(v.top)
        ? Math.max(40, Math.min(150, v.top))
        : 100,
    range: v.range === 40 || v.range === 80 || v.range === 100 ? v.range : 60,
  };
}
export function loadSpectrumOptions(): SpectrumOptions {
  try {
    return normalizeSpectrumOptions(
      JSON.parse(localStorage.getItem("spl-spectrum-v2") ?? "{}"),
    );
  } catch {
    return spectrumDefaults;
  }
}
