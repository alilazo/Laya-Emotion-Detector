import { describe, expect, it } from "vitest";
import { position, radius, stableOffset, VERTICES } from "./math";

describe("constellation positioning", () => {
  it("places pure emotions at their vertices", () => {
    expect(position({ anxiety: 1, sadness: 0, fear: 0 })).toEqual(
      VERTICES.anxiety,
    );
    expect(position({ anxiety: 0, sadness: 1, fear: 0 })).toEqual(
      VERTICES.sadness,
    );
    expect(position({ anxiety: 0, sadness: 0, fear: 1 })).toEqual(
      VERTICES.fear,
    );
  });
  it("places equal weights at the centroid", () => {
    const point = position({ anxiety: 1 / 3, sadness: 1 / 3, fear: 1 / 3 });
    expect(point.x).toBeCloseTo(450);
    expect(point.y).toBeCloseTo(310);
  });
  it("keeps node size bounded and offset deterministic", () => {
    expect(radius(0)).toBe(6);
    expect(radius(100)).toBe(18);
    expect(stableOffset("abc")).toEqual(stableOffset("abc"));
  });
});
