"""failure-swing (TTrades own voice, contested) — batch structure_own_03a.

Claim tested (the positive use, both definitions agree on it): failure swings are
TARGETS, not levels to trade away from — "when failure swings are present, expect those
levels to be revisited and taken out" (Nlw-PZhoViQ); "use the first failure swing as a
target" (yaml). So: a failure-swing level is taken within the horizon more often than a
geometry-matched null level (same signed distance from price, same M1-bar horizon, at
matched random moments +/-30 d). rate_test, claim '+'.

TF 15m (yaml ltf 1H/15m). Swings = strict 3-bar swings (swing-point.yaml). Decision =
close of the bar confirming the newest swing.

Reading a (proximity definition, HbOeD_JVens): two consecutive same-side swings sit
  "close together with no valid separation": |H_k - H_{k-1}| <= 0.25 x ATR14 and nothing
  between them traded above the higher of the two. Level = the cluster's outer extreme.
Reading b (sweep definition, 'a minor extreme that price makes without sweeping a prior
  extreme'): the new swing high H_k < previous swing high H_{k-1} with no trade above
  H_{k-1} between them (the leg toward L reversed before reaching it). Level = H_k.
Mirror for lows. Hit = any M1 high >= level (low <= level) within 300 M1 bars.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a")
from _common import atr, cl, level_rate, np, pd, summary, swings3  # noqa: E402

CID = "failure-swing"
TF, TOL_ATR, HZN = "15min", 0.25, 300


def detect(m1, reading: str):
    b = cl.build_bars(m1, TF)
    h = b["high"].to_numpy(float)
    l = b["low"].to_numpy(float)
    a = atr(b, 14)
    sh, sl = swings3(b)
    rows = []
    for bull in (False, True):          # False: highs (level above), True: lows
        x = -l if bull else h
        pts = np.flatnonzero(sl if bull else sh)
        for k in range(1, len(pts)):
            p0, p1 = pts[k - 1], pts[k]
            conf = p1 + 1
            if conf >= len(b) or not np.isfinite(a[conf]):
                continue
            between = x[p0 + 1:p1].max() if p1 - p0 > 1 else -np.inf
            if reading == "a":
                top = max(x[p0], x[p1])
                if abs(x[p1] - x[p0]) > TOL_ATR * a[conf] or between > top:
                    continue
                lvl = top
            else:
                if not (x[p1] < x[p0]) or between >= x[p0]:
                    continue
                lvl = x[p1]
            # still untaken at the decision (the confirming bar did not trade through)
            if x[conf] >= lvl:
                continue
            rows.append((conf, -lvl if bull else lvl, not bull))
    cols = ["decision_time", "available_at", "level", "above"]
    if not rows:
        return pd.DataFrame(columns=cols)
    r = pd.DataFrame(rows, columns=["conf", "level", "above"])
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[r["conf"].to_numpy()])
    ev = pd.DataFrame({"decision_time": ct, "available_at": ct,
                       "level": r["level"].to_numpy(float),
                       "above": r["above"].to_numpy(bool)})
    return ev.sort_values(["decision_time", "above"]).reset_index(drop=True)


def main():
    base = [f"{TF} bars; swings = strict 3-bar swings, confirmed at the close of the next bar",
            "decision = close of the bar confirming the newest swing; level must be untaken "
            "at that close",
            f"hit = level traded through (M1 high >= / low <=) within {HZN} M1 bars",
            "null = same signed distance from the first M1 open after a matched random "
            "moment (+/-30 d, locked reps/seed), same side, same M1-bar horizon"]
    params = {"tf": TF, "swing": "3-bar strict", "horizon_m1_bars": HZN}
    src = {"tf": "corpus: failure-swing.yaml timeframes ltf ['1H','15m']",
           "swing": "corpus: swing-point.yaml 'Swing high := high[i] > high[i-1] AND high[i] > high[i+1]'",
           "horizon_m1_bars": "declared-before-run: 20 bars of 15m (an intraday target; "
                              "yaml 'use the first failure swing as a target')"}
    for reading, extra, xp, xs in (
            ("a", [f"reading a: consecutive same-side swings within {TOL_ATR} x ATR14 of each "
                   "other, nothing between above the higher; level = cluster outer extreme"],
             {"tol_atr": TOL_ATR},
             {"tol_atr": "declared-before-run: 'close together' is unquantified (yaml "
                         "ambiguity; method_spec §9.3 GAP); 0.25 ATR14 as the equal-highs tolerance"}),
            ("b", ["reading b: new swing high below the previous swing high, nothing between "
                   "traded through the previous one (failed to sweep); level = the new swing"],
             {}, {})):
        ev = cl.cache_frame(f"fs_{reading}_{TF}_{TOL_ATR}", lambda: detect(cl.load_m1(), reading))
        print(reading, len(ev), ev["above"].mean())
        probe = cl.probe_lookahead(lambda m: detect(m, reading), ev, lookback="10D")
        obs, null_fn = level_rate(ev["decision_time"], ev["level"], ev["above"], HZN)
        res = cl.rate_test(obs, ev["decision_time"], available_at=ev["available_at"],
                           null_fn=null_fn, predictors=ev, claim="+")
        print(f"reading {reading}\n" + summary(res))
        p = cl.write_result(CID, reading, res,
                            operationalization={"rules": base + extra,
                                                "params": {**params, **xp}},
                            params_source={**src, **xs}, script=__file__, probe=probe,
                            notes="The null asks whether ANY level at this distance is taken; "
                                  "a swing just formed sits close to price, which the matched "
                                  "distance absorbs.")
        print("  wrote", p)


if __name__ == "__main__":
    main()
