import { describe, expect, it } from "vitest";
import { riskColor, tierColor } from "../lib/format";

describe("risk/tier colors", () => {
  it("maps risk bands to colors", () => {
    expect(riskColor(10)).toBe("#22c55e"); // low
    expect(riskColor(30)).toBe("#eab308"); // medium
    expect(riskColor(60)).toBe("#f97316"); // high
    expect(riskColor(90)).toBe("#ef4444"); // critical
  });

  it("maps tiers to colors", () => {
    expect(tierColor("LOW")).toBe("#22c55e");
    expect(tierColor("CRITICAL")).toBe("#ef4444");
  });
});
