"""max-expansion-deviation-no-trade (AM Trades, guest): once the week's 4 / 4.5 standard
deviation projection of the manipulation leg has been reached, the weekly range is spent --
no further continuation trades in that direction that week.

Operationalisation (gate on the baseline 1h CISD book, claim '+'):
  - the week = trading week (18:00 NY Sunday roll);
  - the week's manipulation leg = the FIRST 1h CISD of the week (AM Trades anchors the weekly
    projection on the hourly chart, from the leg's extreme to the swing where the CISD
    occurred): leg L = |protected extreme - CISD level (series open)|;
  - max expansion = level -/+ 4 * L (bearish/bullish), i.e. the -4 deviation;
  - reached(t) = price has traded to it between the anchor's decision and t (M1 closed by t);
  - blocked = a later event that week, in the anchor's direction, with reached(t) true;
    allowed = everything else (anchor events, other weeks' events, counter-direction events).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, BASE_PARAMS, BASE_SRC, BASE_RULE

SD = 4.0


def _week_key(t):
    td = cl.trading_day(t)
    sd = td + pd.Timedelta(days=1)
    return (sd - pd.to_timedelta(sd.dayofweek, unit="D")).to_numpy()


def detect(m1):
    ev = cisd_book(m1)
    if ev.empty:
        return ev.assign(allowed=pd.Series(dtype=bool), in_after=pd.Series(dtype=bool))
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    wk = _week_key(t)
    closes = (m1.index + pd.Timedelta(minutes=1)).as_unit("ns").asi8
    tn = t.as_unit("ns").asi8
    pos = np.searchsorted(closes, tn, side="right") - 1          # last M1 closed by t
    hi, lo = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    d = ev["direction"].to_numpy()
    lvl, ext = ev["level"].to_numpy(float), ev["extreme"].to_numpy(float)
    allowed = np.ones(len(ev), bool)
    in_after = np.zeros(len(ev), bool)
    first = {}
    for i in range(len(ev)):
        k = wk[i]
        if k not in first:
            first[k] = i
            continue
        a = first[k]
        in_after[i] = True
        if d[i] != d[a]:
            continue
        L = abs(ext[a] - lvl[a])
        if d[a] == -1:
            proj = lvl[a] - SD * L
            reached = lo[pos[a] + 1: pos[i] + 1].min(initial=np.inf) <= proj
        else:
            proj = lvl[a] + SD * L
            reached = hi[pos[a] + 1: pos[i] + 1].max(initial=-np.inf) >= proj
        allowed[i] = not reached
    ev["allowed"] = allowed
    ev["in_after"] = in_after
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("rg02b_maxexp_1hcisd_sd4", lambda: detect(cl.load_m1()))
    print(len(ev), "events; blocked", (~ev["allowed"]).sum(), "later-in-week", ev["in_after"].sum())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "allowed", mask_available_at="decision_time", max_hold="10h", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [BASE_RULE,
                    "week = trading week (18:00 NY roll, Sunday open)",
                    "manipulation leg = first 1h CISD of the week: from its protected extreme to its CISD level (series open)",
                    "max expansion = CISD level -/+ 4 x leg (the -4 deviation) in the anchor's direction",
                    "reached = any M1 bar between the anchor's decision and the event's decision trades to it",
                    "blocked = later same-week event in the anchor's direction after reached; allowed = the rest"],
          "params": {**BASE_PARAMS, "sd_level": SD, "anchor": "first 1h CISD of the trading week",
                     "leg": "protected extreme to CISD series-open level"}}
    src = {**BASE_SRC,
           "sd_level": "corpus: wGYde-h84cs '4 and 4.5 ... max expansion' (4 = first touch of the band)",
           "anchor": "declared-before-run: AM Trades anchors the weekly projection on the hourly manipulation leg (standard-deviation-projection, wGYde-h84cs); first hourly CISD of the week taken as that leg",
           "leg": "corpus: standard-deviation-projection (leg extreme to the swing where the CISD occurred)"}
    p = cl.write_result("max-expansion-deviation-no-trade", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Single worked example in corpus; opposite-direction trades left allowed (not addressed by the rule).")
    print(p)
