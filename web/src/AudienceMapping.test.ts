import { describe, expect, it } from "vitest";
import { mappingOffset } from "./AudienceMapping";
describe("audience mapping energy", () => {
  it("preserves equal levels and offset direction", () => {
    expect(mappingOffset([80, 84, 84, 84, 80])).toBeCloseTo(4, 10);
    expect(mappingOffset([90, 84, 84, 84, 90])).toBeCloseTo(-6, 10);
  });
  it("averages energy rather than dB", () => {
    const result = mappingOffset([80, 80, 90, 80, 80]);
    expect(result).toBeCloseTo(10 * Math.log10(4), 10);
  });
  it("rejects drift and incomplete captures", () => {
    expect(() => mappingOffset([80, 80, 80, 80, 83])).toThrow();
    expect(() => mappingOffset([80, 80])).toThrow();
  });
});
