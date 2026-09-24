// Market-structure zigzag for the /chart page.
//
// A TypeScript port of the research reference, kept in exact parity by zigzag.test.ts:
//   ClaudeTradingRD/market_structure/build_foundation.zigzag_pct (one_pivot_per_bar=True)
//   ClaudeTradingRD/plot_xau.swing_labels / hh_ll_path
// Drawing aid only: a pivot is known only once price has reversed `pct`% from it, and the
// last pivot is the still-developing extreme, so it repaints.

export interface Bar {
  time: number;
  high: number;
  low: number;
}

export type PivotKind = "H" | "L";
export type SwingLabel = "H" | "L" | "HH" | "LH" | "HL" | "LL";

export interface Pivot {
  time: number;
  price: number;
  kind: PivotKind;
}

export interface LabelledPivot extends Pivot {
  label: SwingLabel;
}

/**
 * Alternating H/L pivots on high/low. A leg confirms once price reverses `pct`% from the
 * running extreme, and only on a bar AFTER the one that set it — so a single wide candle can
 * never carry both an H and an L (its intrabar order is unknown).
 */
export function zigzag(bars: Bar[], pct: number): Pivot[] {
  const n = bars.length;
  if (n === 0) return [];
  const r = pct / 100;
  const raw: [number, number, PivotKind][] = []; // [bar index, price, kind]
  let trend = 0; // 0 unknown, +1 up-leg, -1 down-leg
  let hiI = 0;
  let hi = bars[0].high;
  let loI = 0;
  let lo = bars[0].low;

  for (let i = 1; i < n; i++) {
    const { high, low } = bars[i];
    if (trend >= 0) {
      if (high >= hi) {
        hi = high;
        hiI = i;
      }
      if (hiI < i && low <= hi * (1 - r)) {
        raw.push([hiI, hi, "H"]);
        trend = -1;
        lo = low;
        loI = i;
        continue;
      }
    }
    if (trend <= 0) {
      if (low <= lo) {
        lo = low;
        loI = i;
      }
      if (loI < i && high >= lo * (1 + r)) {
        raw.push([loI, lo, "L"]);
        trend = 1;
        hi = high;
        hiI = i;
      }
    }
  }
  // tail: the still-developing extreme, so the line reaches the edge
  if (trend >= 0) raw.push([hiI, hi, "H"]);
  else raw.push([loI, lo, "L"]);

  // collapse consecutive same-kind pivots, keeping the more extreme
  const out: [number, number, PivotKind][] = [];
  for (const p of raw) {
    const last = out[out.length - 1];
    if (last && last[2] === p[2]) {
      if ((p[2] === "H" && p[1] >= last[1]) || (p[2] === "L" && p[1] <= last[1])) {
        out[out.length - 1] = p;
      }
      continue;
    }
    out.push(p);
  }
  return out.map(([i, price, kind]) => ({ time: bars[i].time, price, kind }));
}

/** H/L for the first high/low, then each high vs the previous high (HH/LH) and each low vs
 *  the previous low (HL/LL). An exact tie keeps the plain H/L. */
export function swingLabels(pivots: Pivot[]): LabelledPivot[] {
  const last: Record<PivotKind, number | null> = { H: null, L: null };
  return pivots.map((p) => {
    const prev = last[p.kind];
    let label: SwingLabel = p.kind;
    if (prev !== null && p.price !== prev) {
      label = p.kind === "H" ? (p.price > prev ? "HH" : "LH") : p.price > prev ? "HL" : "LL";
    }
    last[p.kind] = p.price;
    return { ...p, label };
  });
}

/** The trend line: only HH and LL pivots, strictly alternating HH -> LL -> HH -> LL. When two
 *  of the same kind follow each other, the more extreme one is kept. */
export function hhLlPath(
  pivots: Pivot[],
  labels: LabelledPivot[],
): { time: number; price: number }[] {
  const path: { time: number; price: number; label: SwingLabel }[] = [];
  pivots.forEach((p, k) => {
    const label = labels[k].label;
    if (label !== "HH" && label !== "LL") return;
    const last = path[path.length - 1];
    if (last && last.label === label) {
      if ((label === "HH" && p.price >= last.price) || (label === "LL" && p.price <= last.price)) {
        path[path.length - 1] = { time: p.time, price: p.price, label };
      }
      return;
    }
    path.push({ time: p.time, price: p.price, label });
  });
  return path.map(({ time, price }) => ({ time, price }));
}
