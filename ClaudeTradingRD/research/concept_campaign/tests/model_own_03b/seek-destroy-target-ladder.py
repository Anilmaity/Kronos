"""seek-destroy-target-ladder — on a seek-and-destroy (consolidation) day, trade every
deviation out of the range back into it; targets (1) range equilibrium, (2) OTE of
the leg, (3) the opposite side of the range.

Range = the Asia consolidation (20:00-00:00 NY). The profile is identified once
both Asia extremes have been taken (method_spec §2.5: London takes both Asia
extremes). A deviation = a 15m candle (02:00-12:00 NY) that trades beyond an Asia
boundary and closes back inside the range. Entry at its close, stop beyond the
deviation extreme.
Reading a: target rung 1 = range EQ.   Reading b: target rung 3 = opposite side.
Rung 2 (OTE of "the leg") is not tested: the leg is unspecified (outer range or
individual leg used interchangeably) and OTE is on the speaker's excluded list.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "seek-destroy-target-ladder"
ASIA = ("20:00", "00:00")
DEV_WIN = ("02:00", "12:00")


def detect(m1, rung):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    b = cl.build_bars(m1, "15min")[["open", "high", "low", "close", "close_time"]].copy()
    b["tday"] = cl.trading_day(b.index)
    b["asia"] = cl.in_window(b.index, *ASIA)
    b["dev"] = cl.in_window(b.index, *DEV_WIN)
    rows = []
    for td, g in b.groupby("tday", sort=True):
        a = g[g["asia"]]
        if len(a) < 12:                         # need a real Asia session (>= 3h of bars)
            continue
        ah, al = a["high"].max(), a["low"].min()
        eq = (ah + al) / 2
        post = g[g.index >= a.index[-1] + pd.Timedelta(minutes=15)]
        if post.empty:
            continue
        took_hi = (post["high"] > ah).cummax().to_numpy()
        took_lo = (post["low"] < al).cummax().to_numpy()
        both = took_hi & took_lo
        hi, lo, c = post["high"].to_numpy(), post["low"].to_numpy(), post["close"].to_numpy()
        dev = post["dev"].to_numpy()
        sess_end = (pd.Timestamp(td).tz_localize("America/New_York")
                    + pd.Timedelta(days=1, hours=17)).tz_convert("UTC")
        for i in range(len(post)):
            if not (dev[i] and both[i]):
                continue
            t = pd.Timestamp(post["close_time"].iloc[i])
            if hi[i] > ah and al < c[i] < ah:          # buyside deviation -> short
                tgt = eq if rung == "eq" else al
                if c[i] > tgt:
                    rows.append((t, -1, float(hi[i]), float(tgt), sess_end - t))
            elif lo[i] < al and al < c[i] < ah:        # sellside deviation -> long
                tgt = eq if rung == "eq" else ah
                if c[i] < tgt:
                    rows.append((t, 1, float(lo[i]), float(tgt), sess_end - t))
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px", "max_hold"])
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True)
    out["available_at"] = out["decision_time"]
    out["max_hold"] = pd.to_timedelta(out["max_hold"])
    return out[cols]


def detect_a(m1):
    return detect(m1, "eq")


def detect_b(m1):
    return detect(m1, "opp")


RULES = [
    "range = Asia session 20:00-00:00 NY high/low of the trading day (>= 12 15m bars)",
    "seek-and-destroy identified at a bar once both the Asia high and the Asia low have been traded through after 00:00 NY (London/NY took both sides)",
    "deviation = a 15m bar starting 02:00-12:00 NY on an identified day that trades beyond an Asia boundary and closes back inside the Asia range; every deviation is traded",
    "enter next M1 open after its close, back into the range; stop = the deviation bar's extreme",
    "exit at the session end 17:00 NY if neither stop nor target hit",
]
PARAMS = {"range": "Asia 20:00-00:00 NY", "dev_window": "02:00-12:00 NY", "tf": "15min",
          "identification": "both Asia extremes taken", "stop": "deviation extreme",
          "max_hold": "to 17:00 NY"}
SRC = {"range": "session_window_fit: Asia 20:00-00:00 (killzones.yaml forex, verbatim); method_spec §2.5 S&D is framed on the Asia range",
       "dev_window": "method_spec: §2.5 London 02:00-05:00 + NY a.m. to 12:00",
       "tf": "corpus: concept timeframes.ltf 15m",
       "identification": "method_spec: §2.5 'London takes both Asia extremes'",
       "stop": "corpus: yaml execution.stop 'Beyond the deviation extreme'",
       "max_hold": "declared-before-run: intraday profile, flat by the 17:00 NY halt"}


def run(reading, fn, key, rung_rule, rung_param):
    ev = cl.cache_frame(key, lambda: fn(cl.load_m1()))
    print(reading, len(ev))
    probe = cl.probe_lookahead(fn, ev, lookback="5D")
    res = cl.trade_test(ev, claim="+")
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties", "ctrl_overlap")})
    print(cl.write_result(CID, reading, res,
                          operationalization={"rules": RULES + [rung_rule], "params": {**PARAMS, "target": rung_param}},
                          params_source={**SRC, "target": "corpus: PlZD45uLPjE 'one equilibrium two OTE and then three the other side of the range'"},
                          script=__file__, probe=probe,
                          notes="Rung 2 (OTE) not tested: leg unspecified; OTE is on the speaker's own excluded list."))


def main():
    run("a", detect_a, "sdtl_a_v1", "target = rung 1, the Asia range EQ (skip if the close is already past it)", "range EQ")
    run("b", detect_b, "sdtl_b_v1", "target = rung 3, the opposite Asia boundary", "opposite range boundary")


if __name__ == "__main__":
    main()
