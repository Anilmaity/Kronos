import { describe, expect, it } from "vitest";
import { mergeLatest, prependOlder, type Candle } from "./candles";

const c = (time: number, close = time): Candle => ({ time, open: close, high: close, low: close, close });

describe("mergeLatest — the 10s poll", () => {
  it("keeps scrolled-back history and replaces the overlapping tail", () => {
    const loaded = [c(1), c(2), c(3), c(4)];
    const latest = [c(3, 30), c(4, 40), c(5)]; // bar 4 still forming -> updated close
    expect(mergeLatest(loaded, latest)).toEqual([c(1), c(2), c(3, 30), c(4, 40), c(5)]);
  });

  it("returns the latest page on first load", () => {
    expect(mergeLatest([], [c(1), c(2)])).toEqual([c(1), c(2)]);
  });

  it("keeps history when a poll returns nothing", () => {
    expect(mergeLatest([c(1)], [])).toEqual([c(1)]);
  });
});

describe("prependOlder — scroll-back pages", () => {
  it("adds strictly older bars in front and reports how many", () => {
    const { candles, added } = prependOlder([c(5), c(6)], [c(3), c(4), c(5, 99)]);
    expect(candles).toEqual([c(3), c(4), c(5), c(6)]);
    expect(added).toBe(2);
  });

  it("reports 0 when the page has nothing older (start of history)", () => {
    expect(prependOlder([c(5)], [c(5), c(6)]).added).toBe(0);
    expect(prependOlder([c(5)], []).added).toBe(0);
  });

  it("sorts an unsorted page and drops duplicate times", () => {
    const { candles } = prependOlder([c(9)], [c(4), c(2), c(4), c(3)]);
    expect(candles.map((x) => x.time)).toEqual([2, 3, 4, 9]);
  });
});
