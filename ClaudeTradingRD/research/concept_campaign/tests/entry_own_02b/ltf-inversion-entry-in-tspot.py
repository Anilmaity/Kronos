"""ltf-inversion-entry-in-tspot (contested) — batch entry_own_02b.

4jU547ocod4 / gLul2OZQe9Q: after a higher-timeframe candle 2 closure (sweep of the
previous candle's extreme, close back inside) aligned by a lower-timeframe change in
the state of delivery, let price trade into the T-spot during candle 3, drop one more
timeframe and wait for an INVERSION (an opposing FVG closed back through); enter on
that close, stop on the swing that formed the wick; target 2R, or exit at the HTF close.

Stack: 1h C2 / 5m CISD alignment / 1m inversion (the video's hourly / 5-minute /
1-minute stack). T-spot derivation is withheld by the author (method spec §3.7, §9);
the declared stand-in is the half of C2's range on the wick side: [C2 low, C2 EQ] for
a bullish model ("in one example the T-spot is just the equilibrium").

reading a: 2R target (max hold 5h).  reading b: no target, time exit at C3's close.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl                                    # noqa: E402
from detectors.cisd import cisd_events                      # noqa: E402
from _common import M1, to_ts, ns, ONE_MIN                  # noqa: E402

HTF, LTF = "1h", "5min"
RR = 2.0
MAX_HOLD_A = "5h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "c3_close"]


def _detect(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) < 3000:
        return pd.DataFrame(columns=COLS)
    hb = cl.build_bars(m1, HTF)
    ho, hh, hl, hc = (hb[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    hst, hct = ns(hb.index), ns(hb["close_time"])
    lb = cl.build_bars(m1, LTF)
    lst = ns(lb.index)
    lct = ns(lb["close_time"])
    ce = cisd_events(lb[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if len(ce):
        c_dir = np.where(ce["direction"] == "bullish", 1, -1)
        c_conf = lct[np.searchsorted(lst, ns(ce["confirm_time"]))]   # confirm bar close
        c_conf_start = ns(ce["confirm_time"])
    else:
        c_dir = c_conf = c_conf_start = np.zeros(0, dtype="int64")
    m = M1(m1)
    last_ok = m.t[-1] + ONE_MIN
    rows = []
    for i in range(1, len(hb) - 1):
        if hct[i] > last_ok or hst[i + 1] != hct[i]:
            continue                                   # C3 must open right at C2's close
        for up in (True, False):
            if up and not (hl[i] < hl[i - 1] and hc[i] > hl[i - 1]):
                continue
            if (not up) and not (hh[i] > hh[i - 1] and hc[i] < hh[i - 1]):
                continue
            # 5m alignment inside C2
            al = (c_dir == (1 if up else -1)) & (c_conf_start >= hst[i]) & (c_conf <= hct[i])
            if not al.any():
                continue
            ext = hl[i] if up else hh[i]
            eq = (hh[i] + hl[i]) / 2.0
            i0 = int(np.searchsorted(m.t, hst[i + 1], "left"))
            i1 = int(np.searchsorted(m.t, hct[i + 1], "left"))
            tagged = False
            gaps = []                                  # (stamp_idx, level_to_close_through)
            wick = np.inf if up else -np.inf
            for k in range(i0, i1):
                if (m.l[k] < ext) if up else (m.h[k] > ext):
                    break                              # T-spot extreme taken: invalid
                wick = min(wick, m.l[k]) if up else max(wick, m.h[k])
                if (m.l[k] <= eq) if up else (m.h[k] >= eq):
                    tagged = True
                # inversion check against gaps stamped before k
                if tagged and gaps:
                    thr = min(g[1] for g in gaps) if up else max(g[1] for g in gaps)
                    if (m.c[k] > thr) if up else (m.c[k] < thr):
                        rows.append((m.t[k] + ONE_MIN, 1 if up else -1, wick, hct[i + 1]))
                        break
                # opposing 1m FVG stamped at k, formed inside C3, overlapping the T-spot
                if k - 2 >= i0:
                    if up and m.h[k] < m.l[k - 2]:
                        zlo, zhi = m.h[k], m.l[k - 2]
                        if zlo <= eq and zhi >= ext:
                            gaps.append((k, zhi))
                    if (not up) and m.l[k] > m.h[k - 2]:
                        zlo, zhi = m.h[k - 2], m.l[k]
                        if zhi >= eq and zlo <= ext:
                            gaps.append((k, zlo))
    if not rows:
        return pd.DataFrame(columns=COLS)
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "c3"])
    out = out.drop_duplicates(["t", "direction"]).sort_values("t").reset_index(drop=True)
    dec = to_ts(out["t"])
    return pd.DataFrame({"decision_time": dec, "available_at": dec,
                         "direction": out["direction"].to_numpy(),
                         "stop_px": out["stop_px"].to_numpy(float),
                         "c3_close": to_ts(out["c3"])})


OP_RULES = [
    "C2 (1h): low < prior low and close > prior low (bullish; bearish mirror); C3 = the next 1h bar opening at C2's close",
    "alignment: a 5m CISD (series_open, 2/2, max_wait 3) in the model direction confirmed inside C2 (start >= C2 open, "
    "confirm bar close <= C2 close)",
    "T-spot (declared stand-in, derivation withheld): [C2 low, C2 EQ] for bullish ([C2 EQ, C2 high] bearish); "
    "tagged when a C3 M1 bar trades to the EQ; invalid once C3 trades beyond C2's extreme",
    "inversion (1m): a bearish 1m FVG formed inside C3 whose zone overlaps the T-spot, then a later 1m CLOSE above its "
    "top (whole gap) after the T-spot was tagged; decide at that close, enter next M1 open",
    "stop = the wick extreme of C3 so far (the swing that formed the wick)"]
OP_A = {"rules": OP_RULES + ["reading a: target 2R, max hold 5h"],
        "params": {"stack": "1h/5m/1m", "tspot": "C2 wick-side half [extreme, EQ]", "rr": RR,
                   "max_hold": MAX_HOLD_A, "cisd": "series_open 2/2 max_wait 3", "ctrl_tod_tol_min": 30}}
OP_B = {"rules": OP_RULES + ["reading b: no target; time exit at C3's close (max_hold per row = C3 close - decision; rows with zero time left dropped)"],
        "params": {"stack": "1h/5m/1m", "tspot": "C2 wick-side half [extreme, EQ]",
                   "exit": "HTF (C3) candle close", "cisd": "series_open 2/2 max_wait 3", "ctrl_tod_tol_min": 30}}
SRC = {"stack": "corpus: gLul2OZQe9Q 'wait for an inversion to form, take my entry, and then look for 2 R' "
                "(hourly model, 5-minute confirmation, 1-minute entry; YAML execution)",
       "tspot": "declared-before-run: method_spec §3.7 'in one example, simply the equilibrium'; t-spot rule 20 "
                "'the EQ of the candle being traded from'; the indicator's derivation is withheld",
       "rr": "corpus: gLul2OZQe9Q 'and then look for 2 R'",
       "max_hold": "declared-before-run: 5 HTF bars",
       "exit": "corpus: YAML execution target 'a time-based exit at the higher-timeframe candle close (11:00 in the hourly examples)'",
       "cisd": "phase3: rung-0 CISD config",
       "ctrl_tod_tol_min": "declared-before-run: README trap 9"}

def detect_a(m1):
    ev = _detect(m1)
    out = ev[["decision_time", "available_at", "direction", "stop_px"]].copy()
    out["rr"] = RR
    return out


def detect_b(m1):
    ev = _detect(m1)
    out = ev[["decision_time", "available_at", "direction", "stop_px"]].copy()
    out["rr"] = np.nan
    out["max_hold"] = pd.to_timedelta(pd.DatetimeIndex(ev["c3_close"]) - pd.DatetimeIndex(ev["decision_time"]))
    # an inversion closing on C3's last minute leaves no time before the HTF close: no trade
    return out[out["max_hold"] > pd.Timedelta(0)].reset_index(drop=True)


if __name__ == "__main__":
    todo = sys.argv[1:] or ["a", "b"]
    for rd, fn, op in (("a", detect_a, OP_A), ("b", detect_b, OP_B)):
        if rd not in todo:
            continue
        ev = cl.cache_frame(f"ltf_inv_tspot_{rd}", lambda fn=fn: fn(cl.load_m1()))
        print(rd, len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(fn, ev, lookback="20D")
        print("probe", probe.get("passed"))
        kw = {"max_hold": MAX_HOLD_A} if rd == "a" else {}
        res = cl.trade_test(ev, ctrl_tod_tol_min=30, **kw)
        print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail",
                                       "exposure_bars", "ties", "ctrl_overlap", "sanity")})
        cl.write_result("ltf-inversion-entry-in-tspot", rd, res, operationalization=op,
                        params_source={k: SRC[k] for k in op["params"]}, script=__file__, probe=probe,
                        notes=("Reading a: 2R target, 5h hold." if rd == "a" else
                               "Reading b: time exit at the C3 (HTF) close, no target.")
                        + " T-spot is a declared stand-in (the author withholds its derivation); the positional "
                          "'enter on the open' shortcut variant is not tested.")
