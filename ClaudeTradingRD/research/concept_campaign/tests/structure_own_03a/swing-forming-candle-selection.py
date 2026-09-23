"""swing-forming-candle-selection (TTrades own voice, contested) — batch structure_own_03a.

A selection rule for WHICH opposing candles a closure must clear. Two recorded readings:
  9jvWodPJgVI — "that is when I'm going to ignore those small candles ... I'm just going
                to take this whole move up" as the series (messy areas).
  PQiRV0JMhIQ — "when we have this candle that doesn't form a swing, generally I ignore
                it ... I'm going to use this as the continuation" reference.
Both say: a trigger anchored on candles that do not form a swing is not one he takes.

Baseline book (both readings): the phase-3 bare 15m CISD (series_open, swing 2/2,
max_wait 3), decide at the confirming close, enter next M1 open, stop at the protected
swing, 2R, 150 min. Gate (claim '+': rule-compliant triggers beat the ones he ignores):
Reading a (whole move): bullish case — the whole move down = from the last strict 3-bar
  swing high before the extreme; its level = open of the first down-close candle at/after
  that swing high. Gate = the strict trigger's close ALSO clears the whole-move level
  (in a clean move the two series coincide; in a messy one the strict trigger fires on a
  short run of small candles and the rule would still be waiting).
Reading b (swing-forming reference): gate = the first candle of the strict series forms a
  strict 3-bar swing on its own side (bullish: its high > both neighbours' highs), i.e. the
  reference candle is not one that "doesn't form a swing".
Bearish mirrored.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
from _common import PHASE3, cl, np, pd, summary, swings3  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

CID = "swing-forming-candle-selection"
TF, HOLD = "15min", "150min"


def detect(m1):
    b = cl.build_bars(m1, TF)
    ohlc = b[["open", "high", "low", "close"]]
    ev = cisd_events(ohlc, level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "gate_a", "gate_b"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    sh, sl = swings3(b)
    idx = b.index
    s = idx.get_indexer(pd.DatetimeIndex(ev["series_start"]))
    x = idx.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    j = idx.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    bull = (ev["direction"] == "bullish").to_numpy()
    n = len(b)
    ga = np.zeros(len(ev), bool)
    gb = np.zeros(len(ev), bool)
    sh_pos = np.flatnonzero(sh)
    sl_pos = np.flatnonzero(sl)
    for r in range(len(ev)):
        si, xi, ji = s[r], x[r], j[r]
        # reading b: the series' first candle forms a strict 3-bar swing on its side
        if 1 <= si < n - 1:
            gb[r] = bool(sh[si]) if bull[r] else bool(sl[si])
        # reading a: whole-move level from the last opposite swing before the extreme
        piv = sh_pos if bull[r] else sl_pos
        k = np.searchsorted(piv, xi, side="left") - 1     # last pivot strictly before xi
        if k < 0:
            ga[r] = True                                   # no earlier pivot: series = move
            continue
        q = piv[k]
        opp = (c < o) if bull[r] else (c > o)
        first = q + int(np.argmax(opp[q:xi + 1])) if opp[q:xi + 1].any() else si
        lvl_w = o[min(first, si)]
        ga[r] = (c[ji] > lvl_w) if bull[r] else (c[ji] < lvl_w)
    close = pd.DatetimeIndex(b["close_time"].to_numpy()[j])
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(bull, 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                        "gate_a": ga, "gate_b": gb})
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    ev = cl.cache_frame(f"sfcs_cisd_{TF}_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev[["gate_a", "gate_b"]].mean().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    base = ["baseline: 15m bare CISD (series_open, swing 2/2, max_wait 3), decide at the "
            "confirming bar close, enter next M1 open, stop protected swing, 2R, 150 min"]
    params = {"tf": TF, "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
              "rr": 2.0, "max_hold": HOLD, "swing_test": "strict 3-bar"}
    src = {"tf": "corpus: swing-forming-candle-selection.yaml timeframes ltf 15m (15-minute "
                 "protected swing under a 4-hour read)",
           "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "swing_test": "corpus: yaml ambiguity 'the three-bar swing definition from the "
                         "companion relevant-swings video is the only candidate test'"}
    for reading, col, rule in (
            ("a", "gate_a", "gate a: the strict trigger close also clears the whole-move level "
                            "(open of the first opposing-close candle after the last strict "
                            "3-bar opposite swing before the extreme)"),
            ("b", "gate_b", "gate b: the strict series' first candle forms a strict 3-bar swing "
                            "(bullish: its high above both neighbours; bearish: its low below)")):
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD)
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": base + [rule], "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes="Both gates use only bars closed by the confirming bar "
                                  "(the swing test on the series' first candle needs its right "
                                  "neighbour, which precedes the confirming bar).")
        print("  wrote", p)


if __name__ == "__main__":
    main()
