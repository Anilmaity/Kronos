"""mechanical-trade-management (guest: Ash Trades; contested by AP, DTR) - trade_tests.

Ash: entry, stop and 2R target are set at entry and never touched - no break-even, no
trim, no trail. AP/DTR manage "by feel" with no stated rule (yaml: "their side of the
conflict cannot be backtested as specified"), so the testable side is Ash's, against
the two concrete management alternatives it refuses. Trailing has no rule anywhere in
the unit and is not tested.

Baseline trades (declared before run): every 15m bare CISD (series_open, 2/2, max_wait 3)
entered at the next M1 open, stop at the protected swing, 2R target, 150-min clock hold
(phase-3 rung 0). Fixed and managed versions of a trade differ ONLY after the
management trigger, so each reading scores exactly that difference as a new decision:

 (a) NO BREAK-EVEN. Fixed vs "stop to entry at +1R" differ only on trades that tag +1R
     and then come back to the entry price before the target. At that retest BE is
     flat (0R); fixed keeps the original stop and target. Event: decision at the close
     of the first M1 bar after the +1R tag whose extreme reaches the entry price
     (target not hit since the tag); direction, stop_px and target_px = the ORIGINAL
     ones; max_hold = the original hold's remaining time. claim '+': holding from the
     retest beats a matched random entry (Ash: "would have stopped a trailed position
     at break even, then ran to 2R"). avg_R_gross is also the absolute fixed-minus-BE
     R per affected trade, since BE books 0 there.
 (b) NO TRIM. Fixed vs "take a partial at +1R" differ only on the part kept past the
     first +1R tag. Event: decision at the close of the M1 bar that first tags +1R
     (no stop before or in it, target not in it); original stop and target, remaining
     hold. claim '+': the held remainder beats a matched random entry of the same
     geometry (a trim banks the level instead).

Retest bars that also reach the ORIGINAL stop (fixed loses the full 1R inside the very
bar where BE would exit flat) cannot be scored as a later entry; they are dropped and
counted in notes (that exclusion favours the claim, so it is reported).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl   # noqa: E402
import _book as bk         # noqa: E402
from concept_lab.data import utc_ns   # noqa: E402
from concept_lab.engine import Market   # noqa: E402

CID = "mechanical-trade-management"
TRIGGER_R = 1.0
TOD_TOL = 30
HOLD_BARS_MAX = 151          # a 150-min clock hold spans at most 150 M1 bars
DIAG = {}


def _paths(m1):
    """Per baseline trade: the M1 path inside its hold, oriented so long == up."""
    raw = bk.raw_cisd(m1)
    mkt = Market(m1)
    N = len(mkt.tn)
    dec = pd.DatetimeIndex(raw["decision_time"])
    dn = utc_ns(dec)
    sgn = raw["direction"].to_numpy(np.int64)
    stop = raw["stop_px"].to_numpy(float)
    i0 = np.searchsorted(mkt.tn, dn, side="left")
    end_ns = dn + bk.MAX_HOLD.value
    i1 = np.searchsorted(mkt.tn, end_ns, side="left")
    ok = (i0 < N) & (i1 > i0)
    i0c = np.clip(i0, 0, N - 1)
    entry = mkt.o[i0c]
    risk = sgn * (entry - stop)
    ok &= np.isfinite(risk) & (risk > 0)
    k = np.flatnonzero(ok)
    return raw, mkt, k, sgn, stop, entry, risk, i0, i1, end_ns


def _scan(m1, reading):
    raw, mkt, k, sgn, stop, entry, risk, i0, i1, end_ns = _paths(m1)
    N = len(mkt.tn)
    rows = []
    n_drop_stop_in_retest = 0
    CH = 4000
    ar = np.arange(HOLD_BARS_MAX)
    for s in range(0, len(k), CH):
        kk = k[s:s + CH]
        idx = i0[kk][:, None] + ar[None, :]
        inwin = idx < i1[kk][:, None]
        idc = np.minimum(idx, N - 1)
        g = sgn[kk][:, None]
        up = np.where(g > 0, mkt.h[idc], -mkt.l[idc])        # favourable extreme
        dnx = np.where(g > 0, mkt.l[idc], -mkt.h[idc])       # adverse extreme
        e = (sgn[kk] * entry[kk])[:, None]
        r = risk[kk][:, None]
        st = e - r
        tg = e + 2.0 * r
        one = e + TRIGGER_R * r
        hit_stop = (dnx <= st) & inwin
        hit_tgt = (up >= tg) & inwin
        hit_one = (up >= one) & inwin
        first = lambda m: np.where(m.any(1), m.argmax(1), HOLD_BARS_MAX)   # noqa: E731
        f_stop, f_tgt, f_one = first(hit_stop), first(hit_tgt), first(hit_one)
        # +1R tagged strictly before any stop, and not in a bar that stops or targets
        tagged = (f_one < HOLD_BARS_MAX) & (f_one < f_stop) & (f_one < f_tgt)
        for j in np.flatnonzero(tagged):
            t1 = f_one[j]
            if reading == "b":
                pos = i0[kk[j]] + t1
            else:
                back = (dnx[j] <= e[j, 0]) & inwin[j]
                back[:t1 + 1] = False
                if not back.any():
                    continue
                t2 = int(back.argmax())
                if f_tgt[j] <= t2:            # target reached first: BE never matters
                    continue
                if dnx[j, t2] <= st[j, 0]:    # retest bar also stops the fixed trade
                    n_drop_stop_in_retest += 1
                    continue
                pos = i0[kk[j]] + t2
            dt = mkt.tn[pos] + bk.ONE_MIN
            rem = end_ns[kk[j]] - dt
            if rem <= 0:
                continue
            o = kk[j]
            rows.append((dt, int(sgn[o]), float(stop[o]),
                         float(entry[o] + sgn[o] * 2.0 * risk[o]), int(rem)))
    DIAG["dropped_retest_bar_hits_stop"] = n_drop_stop_in_retest
    if not rows:
        return pd.DataFrame(columns=["decision_time", "available_at", "direction",
                                     "stop_px", "target_px", "max_hold"])
    a = np.array([r[0] for r in rows], dtype=np.int64)
    t = pd.DatetimeIndex(pd.to_datetime(a, utc=True))
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": [r[1] for r in rows],
                        "stop_px": [r[2] for r in rows],
                        "target_px": [r[3] for r in rows],
                        "max_hold": pd.to_timedelta([r[4] for r in rows], unit="ns")})
    return out.sort_values(["decision_time", "direction", "stop_px"],
                           ascending=[True, False, True], kind="stable").reset_index(drop=True)


def detect_a(m1):
    return _scan(m1, "a")


def detect_b(m1):
    return _scan(m1, "b")


def run(reading, detect, rules, notes):
    ev = cl.cache_frame(f"{CID}_{reading}_{TRIGGER_R}", lambda: detect(cl.load_m1()),
                        version=bk.VERSION)
    diag = dict(DIAG)
    print(reading, len(ev), diag)
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.trade_test(ev, ctrl_tod_tol_min=TOD_TOL, claim="+")
    for k in ("n", "avg_R", "avg_R_gross", "win_rate", "diff", "ci_lo", "ci_hi", "p",
              "mde", "verdict", "verdict_detail", "exposure_bars", "ties", "dropped"):
        print(" ", k, res.get(k))
    op = {"rules": ["baseline trades: 15m bare CISD (series_open, 2/2 swings, max_wait 3), "
                    "next-M1-open entry, stop at the protected swing, 2R target, 150-min "
                    "clock hold (every signal; management is per trade)"] + rules,
          "params": {"baseline_tf": bk.TF, "level_rule": "series_open", "swing": "2/2",
                     "max_wait": 3, "rr": 2.0, "max_hold": "150min",
                     "trigger_R": TRIGGER_R, "ctrl_tod_tol_min": TOD_TOL}}
    src = {"baseline_tf": bk.BASE_SOURCES["baseline_tf"],
           "level_rule": bk.BASE_SOURCES["level_rule"], "swing": bk.BASE_SOURCES["swing"],
           "max_wait": bk.BASE_SOURCES["max_wait"],
           "rr": "corpus: zXtJSSkiNmo Ash - limit take-profit at 2R (yaml detection_rules)",
           "max_hold": bk.BASE_SOURCES["max_hold"],
           "trigger_R": "declared-before-run: no trigger level is stated for the refused "
                        "BE move / trim; +1R is the conventional point (half-way to 2R)",
           "ctrl_tod_tol_min": "declared-before-run: not a timing rule; hold the NY "
                               "clock in the control (README trap 9)"}
    notes = notes.replace("{dropped}", str(diag.get("dropped_retest_bar_hits_stop",
                                                     "n/a (frame from cache)")))
    p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
    return res


if __name__ == "__main__":
    ra = run("a", detect_a,
             [f"event (a, no break-even): after the first M1 tag of +{TRIGGER_R}R (no stop "
              "before or in that bar, no target in it), the first later M1 bar whose "
              "adverse extreme reaches the entry price with the target not yet hit; "
              "decide at its close; original direction, stop and 2R target; remaining "
              "hold; claim '+': holding (fixed) beats a matched random entry",
              "retest bars that also reach the original stop are dropped (counted)"],
             "Tests Ash's no-break-even rule on the only trades where BE and fixed "
             "differ. avg_R_gross = absolute fixed-minus-BE R per affected trade (BE books "
             "0 at the retest). Dropped retest bars that also hit the original stop: "
             "{dropped}. FRAGILITY: in each dropped case fixed loses the full 1R inside "
             "the bar where BE exits flat (fixed-minus-BE = -1R). Folding them back in "
             "arithmetically (n=3,344 scored + 37 dropped in the first run) moves the "
             "absolute fixed-minus-BE gross from +0.038R to about +0.027R per affected "
             "trade, and would shift the control-adjusted diff down by ~0.011R - enough "
             "to put the CI's lower end (+0.003) below zero. Treat any EDGE here as "
             "not robust to that exclusion. (Notes-only re-run: same frame, locked seed, "
             "identical statistics.)")
    rb = run("b", detect_b,
             [f"event (b, no trim): the close of the M1 bar that first tags +{TRIGGER_R}R "
              "(no stop before or in it, no target in it); original direction, stop and "
              "2R target; remaining hold; claim '+': the held remainder beats a matched "
              "random entry of the same geometry"],
             "Tests Ash's no-trim rule on the part of each trade a +1R partial would "
             "have banked. Trailing is not tested (no rule stated by anyone in the unit).")
