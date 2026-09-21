import { describe, expect, it } from "vitest";
import { normalizeSpectrumOptions, spectrumDefaults } from "./spectrumOptions";
describe("spectrum controls", () => {
  it("defaults to band steps with useful level scale", () => {
    expect(normalizeSpectrumOptions(null)).toEqual(spectrumDefaults);
  });
  it("rejects corrupt browser preferences", () => {
    expect(
      normalizeSpectrumOptions({
        fraction: 48,
        top: Infinity,
        range: -1,
        averaging: "wrong",
      }),
    ).toEqual(spectrumDefaults);
    expect(normalizeSpectrumOptions({ top: 999 }).top).toBe(150);
  });
});
