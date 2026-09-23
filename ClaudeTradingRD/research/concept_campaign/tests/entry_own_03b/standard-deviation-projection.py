"""standard-deviation-projection — contested (mixed voice; TTrades canon kTWXpAo1uE8,
upHS7SDL9kg, LLuI42YNUko, yVgn2rBhysQ). Two readings, both trade_test.

Anchor (both readings): after a CISD the manipulation leg is 'the low, and the high
that made that low' (bullish) — 'finding the low, then finding the high that made
the low' (LLuI42YNUko); bearish: the high, and the low that made the high. Fib 1 at
the reversal extreme... here: 0 at the ORIGIN of the leg (the swing that made the
extreme), 1 at the extreme, projections -k = origin + k*leg beyond the origin in the
new direction (bearish: origin_low - k*(extreme_high - origin_low)).
Settings 1, 0, -1, -2, -2.5, -4 (kTWXpAo1uE8).

reading a (targets): 'the -2 to -2.5 band is the first target' — the channel's own
  assembly (cisd-entry-model, method_spec §4.7): enter at the CISD close, stop on the
  manipulation extreme, target = the -2 projection (the near edge of the band).
  Claim '+'.
reading b (reaction area): 'the -2 to -2.5 band is where a retracement or reversal is
  expected' — at the first touch of -2 (before the extreme is retaken, within 24h),
  trade the retracement: counter-direction, target back to -1, stop at -4 ('max
  expansion', which a displacement close through the band would promote). Claim '+'.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import _batch_common as bc    # noqa: E402
from _batch_common import cl  # noqa: E402
from detectors.cisd import cisd_events         # noqa: E402

CID = "standard-deviation-projection"
HOLD_A = "12h"
HOLD_B = "150min"
REACH_H = pd.Timedelta(hours=24)
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "target_px"]


def anchors(m1: pd.DataFrame):
    b = bc.bars(m1)
    if len(b) < 50:
        return b, pd.DataFrame()
    cs = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if cs.empty:
        return b, pd.DataFrame()
    is_sh, is_sl = bc.swing_arrays(b)
    h, l = b["high"].to_numpy(float), b["low"].to_numpy(float)
    pos_of = pd.Series(np.arange(len(b)), index=b.index)
    sh_pos, sl_pos = np.flatnonzero(is_sh), np.flatnonzero(is_sl)
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    rows = []
    for _, r in cs.iterrows():
        e = int(pos_of[r["extreme_time"]])
        cf = int(pos_of[r["confirm_time"]])
        d = 1 if r["direction"] == "bullish" else -1
        opp = sh_pos if d == 1 else sl_pos          # the swing that MADE the extreme
        i = np.searchsorted(opp, e) - 1
        if i < 0:
            continue
        p = int(opp[i])
        ext = float(r["extreme_price"])
        org = h[p] if d == 1 else l[p]
        leg = (org - ext) if d == 1 else (ext - org)
        if not leg > 0:
            continue
        rows.append((ct[cf], d, ext, org, leg))
    a = pd.DataFrame(rows, columns=["t", "d", "ext", "org", "leg"])
    return b, a


def proj(a, k):
    # bullish: origin high + k*leg above it; bearish: origin low - k*leg
    return a["org"].to_numpy() + a["d"].to_numpy() * k * a["leg"].to_numpy()


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    b, a = anchors(m1)
    if a.empty:
        return bc.empty(COLS_A)
    t = pd.DatetimeIndex(a["t"])
    ev = pd.DataFrame({"decision_time": t, "available_at": t, "direction": a["d"].to_numpy(),
                       "stop_px": a["ext"].to_numpy(), "target_px": proj(a, 2.0)})
    return bc.finish(ev)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    b, a = anchors(m1)
    if a.empty:
        return bc.empty(COLS_A)
    t = pd.DatetimeIndex(a["t"])
    d = a["d"].to_numpy()
    lv2 = proj(a, 2.0)
    until = t + REACH_H
    # reach of -2 in the projected direction, and retake of the extreme (invalidation)
    hit2, t2 = bc.touch_sided(m1, t, lv2, -d, until)         # 'above' for bullish (d=1 -> -1)
    hitx, tx = bc.touch_sided(m1, t, a["ext"].to_numpy(), d, until)
    ok = hit2 & (~hitx | (tx > t2))
    a, t2 = a[ok], t2[ok]
    ev = pd.DataFrame({"decision_time": t2, "available_at": t2,
                       "direction": -a["d"].to_numpy(),
                       "stop_px": proj(a, 4.0), "target_px": proj(a, 1.0)})
    return bc.finish(ev)


def show(res):
    for k in ["n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "verdict",
              "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "dropped", "exit_mix"]:
        print(" ", k, res.get(k))


BASE = ["15m CISD (series_open, 2/2 swings, within 3 bars) = the reversal; its extreme = "
        "the manipulation extreme",
        "manipulation leg origin = the latest 2/2 swing on the other side before the extreme "
        "('the high that made the low'); leg = |origin - extreme|",
        "projection -k = origin + k*leg in the new direction (fib 0 at the origin, 1 at the extreme)"]
SRC = {"tf": "corpus: standard-deviation-projection.yaml ltf 15m/5m/2m; phase3 primary entry TF",
       "cisd": "phase3: locked CISD config (series_open, 2/2, max_wait 3)",
       "anchor": "corpus: LLuI42YNUko 'finding the low, then finding the high that made the low'",
       "levels": "corpus: kTWXpAo1uE8 'the settings we have here are 1 0 -1 -2 -2.5 and -4'"}


def run_a():
    ev = cl.cache_frame("sdproj_a_15m_cisd_target2", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=HOLD_A)
    show(res)
    op = {"rules": BASE + ["reading a: enter at the next M1 open after the CISD close in the "
                           "reversal direction; stop at the manipulation extreme; target the "
                           "-2 projection (near edge of the -2/-2.5 band); exit after 12h"],
          "params": {"tf": bc.TF, "cisd": "series_open/2-2/mw3", "anchor": "origin swing",
                     "levels": "target -2", "max_hold": HOLD_A}}
    src = {**SRC, "max_hold": "declared-before-run: 12h, a projection target is a session-scale objective (48 entry bars)"}
    return cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                           script=__file__, probe=probe,
                           notes="Reading a tests the projection as the TARGET of the CISD "
                                 "reversal entry (method_spec §4.7 assembly). The matched control "
                                 "shares the target distance, so the differential rates the entry "
                                 "at that projected geometry; the size-conditional -1 branch "
                                 "('large' leg) is unquantified and not applied.")


def run_b():
    ev = cl.cache_frame("sdproj_b_15m_band_reaction", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev))
    probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=HOLD_B)
    show(res)
    op = {"rules": BASE + ["reading b: after the CISD close, the first M1 touch of -2 within "
                           "24h, provided the extreme was not retaken first; trade the "
                           "retracement (against the projected direction) from the next M1 "
                           "open; target -1, stop -4; exit 150 min"],
          "params": {"tf": bc.TF, "cisd": "series_open/2-2/mw3", "anchor": "origin swing",
                     "levels": "entry at -2 touch, target -1, stop -4",
                     "reach_window": "24h", "max_hold": HOLD_B}}
    src = {**SRC, "reach_window": "declared-before-run: the -2 touch must come within 24h of the CISD",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    src["levels"] = ("corpus: kTWXpAo1uE8 'I'm looking for either a retracement or a reversal "
                     "from this area' (-2/-2.5); -4 = max expansion if the band fails; -1 = "
                     "retracement target declared-before-run")
    return cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                           script=__file__, probe=probe,
                           notes="Reading b tests the band as a REACTION area with a matched "
                                 "control at the same stop/target geometry.")


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        print(run_a())
    if "b" in which:
        print(run_b())
