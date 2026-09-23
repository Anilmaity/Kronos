"""relevant-swings-separation (structure, TTrades own voice, contested) — batch structure_own_04b.

Claim (HbOeD_JVens, the dedicated teaching video): relevant swing highs/lows are "the only places
he looks for a reaction or a reversal". A swing sitting close to another same-side extreme beyond
it is a FAILURE swing — "go outward to the extreme and mark that instead"; a swing with visible
separation from the next same-side extreme is relevant and a reversal off it can be trusted.
Measurable (yaml): reversal rate at swings bucketed by separation-to-neighbour distance.

Gate test on a stated baseline book: FADE THE FIRST TOUCH of every confirmed 1h three-candle swing
(method spec §1.1) inside its look-back window (relevant-swing-lookback: hourly chart -> three
days; the touch must come within 2 trading days = 2,760 M1 bars of confirmation). Decision at the
close of the M1 bar that first trades to the swing; long at lows, short at highs; entry next M1
open; stop 0.5 x ATR14(1h) beyond the farther of the swing and the touching bar's extreme; 2R;
10h hold. Gate (relevant) = no untaken same-side confirmed swing lies BEYOND it (lower, for a low)
within 0.5 x ADR (ATR14 of completed daily bars) inside the three-day window at confirmation.
Complement = failure swings (a close outer extreme exists). claim '+'.
All parameters declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04b")
import numpy as np
import pandas as pd
from _common import cl, swing_points, atr, last_before, HOLD, RR

TF = "1h"
WINDOW_DAYS = 3
SEP_ADR = 0.5
SW = (1, 1)
TOUCH_BARS = 2760
STOP_ATR = 0.5


def detect(m1):
    b = cl.build_bars(m1, TF)
    n = len(b)
    h, l = b["high"].to_numpy(float), b["low"].to_numpy(float)
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    a1 = atr(b)
    sw = swing_points(b[["high", "low"]], *SW)
    sh, sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    td = cl.trading_day(b.index)
    dc = pd.factorize(pd.Series(td.to_numpy()), sort=True)[0]
    first = {}
    for k, d in enumerate(dc):
        first.setdefault(d, k)
    d1 = cl.build_bars(m1, "1D")
    rows = []
    R = SW[1]
    for side, flags in (("low", sl), ("high", sh)):
        idx = np.flatnonzero(flags)
        for s in idx:
            c = s + R                              # confirming bar
            if c >= n or not np.isfinite(a1[c]):
                continue
            d = dc[c]
            if d - (WINDOW_DAYS - 1) not in first:
                continue
            w0 = first[d - (WINDOW_DAYS - 1)]
            prev = idx[(idx >= w0) & (idx < s) & (idx + R <= c)]
            if side == "low":
                live = [q for q in prev if l[q + 1:c + 1].min() >= l[q]]
                gaps = [l[s] - l[q] for q in live if l[q] < l[s]]
                lvl = l[s]
            else:
                live = [q for q in prev if h[q + 1:c + 1].max() <= h[q]]
                gaps = [h[q] - h[s] for q in live if h[q] > h[s]]
                lvl = h[s]
            rows.append((side, s, c, lvl, a1[c], min(gaps) if gaps else np.inf))
    if not rows:
        return pd.DataFrame({"decision_time": pd.DatetimeIndex([], tz="UTC"),
                             "available_at": pd.DatetimeIndex([], tz="UTC"),
                             "direction": pd.Series(dtype=int), "stop_px": pd.Series(dtype=float),
                             "rr": pd.Series(dtype=float), "relevant": pd.Series(dtype=bool),
                             "level": pd.Series(dtype=float)})
    S = pd.DataFrame(rows, columns=["side", "s", "c", "level", "atr1h", "gap"])
    S["conf_t"] = ct[S["c"].to_numpy()]
    S["adr"] = last_before(d1["close_time"], atr(d1), S["conf_t"])
    out = []
    for side, g in S.groupby("side"):
        tch = cl.touch(pd.DatetimeIndex(g["conf_t"]), g["level"].to_numpy(),
                       "below" if side == "low" else "above", horizon_bars=TOUCH_BARS, m1=m1)
        g = g.assign(hit=tch["hit"].to_numpy(), hit_time=tch["hit_time"].to_numpy())
        g = g[g["hit"]]
        ht = pd.DatetimeIndex(g["hit_time"]).tz_convert("UTC")
        bar = m1.reindex(ht)
        dec = ht + pd.Timedelta(minutes=1)
        if side == "low":
            ext = np.minimum(g["level"].to_numpy(), bar["low"].to_numpy(float))
            stop = ext - STOP_ATR * g["atr1h"].to_numpy()
            dirn = 1
        else:
            ext = np.maximum(g["level"].to_numpy(), bar["high"].to_numpy(float))
            stop = ext + STOP_ATR * g["atr1h"].to_numpy()
            dirn = -1
        out.append(pd.DataFrame({"decision_time": dec, "available_at": dec, "direction": dirn,
                                 "stop_px": stop, "rr": RR,
                                 "relevant": ~(g["gap"].to_numpy() < SEP_ADR * g["adr"].to_numpy()),
                                 "level": g["level"].to_numpy(), "adr": g["adr"].to_numpy()}))
    ev = pd.concat(out, ignore_index=True)
    ev = ev[np.isfinite(ev["adr"]) & np.isfinite(ev["stop_px"])].drop(columns="adr")
    ev["relevant"] = ev["relevant"].astype(bool)
    return ev.sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"rsws_{TF}_w{WINDOW_DAYS}_s{SEP_ADR}_t{TOUCH_BARS}_k{STOP_ATR}", lambda: detect(cl.load_m1()))
    print(len(ev), float(ev["relevant"].mean()))
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.gate_test(ev, "relevant", mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                                   "exposure_bars", "ties", "ctrl_overlap")})
    op = {"rules": [
        "baseline: fade the first M1 touch of every confirmed 1h three-candle swing within 2,760 M1 bars (the rest of its three-day look-back window); decide at the touching M1 bar's close, enter next M1 open; long at lows, short at highs",
        "stop 0.5 x ATR14(1h) beyond the farther of the swing and the touching bar's extreme; 2R target; 10h wall clock",
        "gate (relevant swing): no untaken same-side confirmed 1h swing lies beyond it within 0.5 x ADR (ATR14 of completed daily bars) in the three-day window at confirmation",
        "complement: failure swing (a close outer same-side extreme exists)",
        "claim: fades at relevant swings beat fades at failure swings (control-adjusted R)"],
        "params": {"tf": TF, "swing": "1/1 fractal", "window_days": WINDOW_DAYS, "touch_bars": TOUCH_BARS,
                   "stop_atr": STOP_ATR, "rr": RR, "max_hold": HOLD[TF], "sep_adr": SEP_ADR,
                   "adr": "ATR14 of completed 1D bars (18:00 NY roll)"}}
    src = {"tf": "phase3: 1h rung-0 timeframe (conjunction_preregistration)",
           "swing": "method_spec: §1.1 swing point = three-candle fractal (yaml detection rule 1)",
           "window_days": "corpus: HbOeD_JVens 'that same look back period of three higher time frame candles' (hourly -> three days)",
           "touch_bars": "declared-before-run: two further trading days (2 x 1,380 M1 bars) = the rest of the three-day window",
           "stop_atr": "declared-before-run: stop 0.5 ATR14(1h) beyond the level (corpus: stop beyond the swing, no distance given)",
           "rr": "phase3: 2R rung-0 target",
           "max_hold": "phase3: 10 entry-TF periods",
           "sep_adr": "declared-before-run: same 0.5 ADR as relevant-swing-separation (corpus instance c7nk7ypJHN4 '400 points' NQ; HbOeD_JVens gives no threshold)",
           "adr": "declared-before-run: ADR as ATR14 of daily bars (yaml measurable 'separation ... in ATR')"}
    p = cl.write_result("relevant-swings-separation", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes=f"gate firing rate {float(ev['relevant'].mean()):.3f} of {len(ev)} first touches. "
                              "The speaker states there is no mechanical separation rule; 0.5 ADR is declared. "
                              "Relevance migration (next swing out becomes relevant) is not modelled.")
    print("wrote", p)
