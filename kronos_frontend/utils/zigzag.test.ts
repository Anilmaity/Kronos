import { describe, expect, it } from "vitest";
import { zigzag, swingLabels, hhLlPath, type Bar } from "./zigzag";
import fixture from "./zigzag.fixture.json";

// The fixture is 600 real XAUUSD 1h bars with the pivots, labels and HH-LL path produced by
// the Python reference (ClaudeTradingRD/market_structure/build_foundation.zigzag_pct with
// one_pivot_per_bar=True, plot_xau.swing_labels, plot_xau.hh_ll_path).
const bars = fixture.bars as Bar[];

describe("zigzag — parity with the Python reference", () => {
  for (const [pct, want] of Object.entries(fixture.cases)) {
    it(`${pct}% pivots, labels and HH-LL path match`, () => {
      const piv = zigzag(bars, Number(pct));
      expect(piv).toEqual(want.pivots);
      const labels = swingLabels(piv);
      expect(labels.map((l) => l.label)).toEqual(want.labels);
      expect(hhLlPath(piv, labels)).toEqual(want.trend);
    });
  }
});

describe("zigzag — structure rules", () => {
  it("never puts two pivots on the same candle", () => {
    for (const pct of [0.5, 1.5, 3]) {
      const times = zigzag(bars, pct).map((p) => p.time);
      expect(new Set(times).size).toBe(times.length);
    }
  });

  it("alternates highs and lows", () => {
    const piv = zigzag(bars, 0.5);
    for (let i = 1; i < piv.length; i++) expect(piv[i].kind).not.toBe(piv[i - 1].kind);
  });

  it("does not let one wide candle be both the high and the low", () => {
    // bar 2 makes a new high AND trades 10% below it: only one pivot may sit on it
    const wide: Bar[] = [
      { time: 1, high: 100, low: 99 },
      { time: 2, high: 110, low: 95 },
      { time: 3, high: 100, low: 96 },
      { time: 4, high: 104, low: 101 },
    ];
    const times = zigzag(wide, 3).map((p) => p.time);
    expect(new Set(times).size).toBe(times.length);
  });

  it("labels the first high/low plainly, then HH/LH and HL/LL", () => {
    const piv = [
      { time: 1, price: 10, kind: "L" as const },
      { time: 2, price: 20, kind: "H" as const },
      { time: 3, price: 12, kind: "L" as const },
      { time: 4, price: 18, kind: "H" as const },
      { time: 5, price: 8, kind: "L" as const },
      { time: 6, price: 25, kind: "H" as const },
    ];
    expect(swingLabels(piv).map((l) => l.label)).toEqual(["L", "H", "HL", "LH", "LL", "HH"]);
  });

  it("joins only HH and LL, strictly alternating, keeping the more extreme repeat", () => {
    const piv = [
      { time: 1, price: 10, kind: "L" as const },
      { time: 2, price: 20, kind: "H" as const },
      { time: 3, price: 12, kind: "L" as const }, // HL: skipped
      { time: 4, price: 22, kind: "H" as const }, // HH
      { time: 5, price: 14, kind: "L" as const }, // HL: skipped
      { time: 6, price: 24, kind: "H" as const }, // HH again: replaces 22
      { time: 7, price: 9, kind: "L" as const }, // LL
    ];
    expect(hhLlPath(piv, swingLabels(piv))).toEqual([
      { time: 6, price: 24 },
      { time: 7, price: 9 },
    ]);
  });
});
