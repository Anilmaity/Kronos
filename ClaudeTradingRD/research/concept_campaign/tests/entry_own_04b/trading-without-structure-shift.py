"""trading-without-structure-shift — contested, two readings (both trade_test).

(a) TTrades (yq4Z7q4E6nU): enter BEFORE any market structure shift. Needs (1) a higher-
    timeframe point of interest and (2) — "the most important" — a run of a short-term
    high/low followed by an aggressive move back into the range; the run-and-return prints a
    fair value gap which is the entry; stop on the low that was run.
    15m: a bar sweeps the most recent unswept confirmed 2/2 swing low while reaching a 1h POI
    (the prior trading day's low, or an active bullish 1h FVG formed in the last 24 1h bars and
    not closed through). Aggressive return: within 4 bars a bar closes back above the swept
    swing low AND a bullish 15m FVG forms in that leg. Entry: limit at the FVG's CE (0.5),
    resting 12 bars, cancelled if the run low trades first. Stop = the run low; 2R; 150 min.
(b) Finessee_Fx (guest, eK_6wgNpNh0): no structure breaks at all — hold ONE bias until an order
    block is violated, and enter on arrival at an array. Bias = the most recent 1h CISD order
    block, held (ignoring newer CISDs) until a 1h close through its protected swing; then the
    next CISD becomes the anchor. Entry: first return to the near edge of a 15m FVG in the bias
    direction formed while the anchor is alive (limit at arrival), within 12 bars. Stop = the
    anchor block's protected swing (where the bias is 'proven wrong'); 2R; 150 min.

All parameters are declared here before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points
from detectors.cisd import cisd_events

TF = "15min"
SWING = 2
RET_BARS = 4            # threshold_fits displacement N-window
FVG1H_LIFE = 24         # 1h FVG POI active for 24 1h bars
FILL_BARS = 12          # limit rests 12 15m bars
RR = 2.0
MAX_HOLD = "150min"
MAX_HOLD_B = "10h"       # reading b: anchor stops are 1h-structure wide
NS = 10**9


def _ns(x) -> np.ndarray:
    return pd.DatetimeIndex(x).tz_convert("UTC").as_unit("ns").asi8 \
        if getattr(pd.DatetimeIndex(x), "tz", None) is not None else \
        pd.DatetimeIndex(x).as_unit("ns").asi8


def _fill(mt, ML, MH, t_from, t_to, level, bull, stop):
    """First M1 in [t_from, t_to) trading into level; None if stop trades first / same bar."""
    a, z = np.searchsorted(mt, t_from), np.searchsorted(mt, t_to)
    for m in range(a, z):
        if bull:
            if ML[m] <= stop:
                return None
            if ML[m] <= level:
                return m
        else:
            if MH[m] >= stop:
                return None
            if MH[m] >= level:
                return m
    return None


def _fvg1h_state(m1):
    """Per 1h FVG: (direction, top, bottom, available_ns, dead_ns)."""
    h = cl.build_bars(m1, "1h")
    H, L, C = h["high"].to_numpy(), h["low"].to_numpy(), h["close"].to_numpy()
    ct = _ns(h["close_time"])
    out = []
    for k in range(2, len(h)):
        for bull in (True, False):
            if bull and L[k] > H[k - 2]:
                top, bot = L[k], H[k - 2]
            elif (not bull) and H[k] < L[k - 2]:
                top, bot = L[k - 2], H[k]
            else:
                continue
            end = min(len(h), k + 1 + FVG1H_LIFE)
            dead = ct[end - 1] if end - 1 > k else ct[k]
            for j in range(k + 1, end):
                if (bull and C[j] < bot) or ((not bull) and C[j] > top):
                    dead = ct[j]
                    break
            out.append((bull, top, bot, ct[k], dead))
    return out


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "poi"]
    b = cl.build_bars(m1, TF)
    if len(b) < 20:
        return pd.DataFrame(columns=cols)
    sw = swing_points(b[["open", "high", "low", "close"]], left=SWING, right=SWING)
    H, L, C = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    ct = _ns(b["close_time"])
    st = _ns(b.index)
    n = len(b)
    pd_ = cl.prior_hilo(pd.DatetimeIndex(b.index), "1D", m1=m1)   # completed day before bar start
    pdl, pdh = pd_["low"].to_numpy(float), pd_["high"].to_numpy(float)
    f1 = _fvg1h_state(m1)
    f_bull = sorted([f for f in f1 if f[0]], key=lambda f: f[3])
    f_bear = sorted([f for f in f1 if not f[0]], key=lambda f: f[3])
    av_bull = np.array([f[3] for f in f_bull], dtype=np.int64)
    av_bear = np.array([f[3] for f in f_bear], dtype=np.int64)
    mt = _ns(m1.index)
    ML, MH = m1["low"].to_numpy(), m1["high"].to_numpy()
    is_sh, is_sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    rows = []
    for bull in (True, False):
        last = np.nan
        swept = True
        fl = f_bull if bull else f_bear
        avs = av_bull if bull else av_bear
        for i in range(n):
            p = i - SWING - 1
            if p >= 0 and (is_sl[p] if bull else is_sh[p]):
                last, swept = (L[p] if bull else H[p]), False
            if swept or np.isnan(last):
                continue
            if not ((L[i] < last) if bull else (H[i] > last)):
                continue
            swept = True
            # HTF POI reached by the sweeping bar (known at its close)
            poi = ""
            if bull and not np.isnan(pdl[i]) and L[i] <= pdl[i]:
                poi = "pdl"
            if (not bull) and not np.isnan(pdh[i]) and H[i] >= pdh[i]:
                poi = "pdh"
            if not poi:
                lo_ = np.searchsorted(avs, st[i] - FVG1H_LIFE * 3600 * NS, side="left")
                hi_ = np.searchsorted(avs, st[i], side="right")
                for (_, top, bot, av, dead) in fl[lo_:hi_]:
                    if dead > st[i]:
                        if (bull and L[i] <= top and H[i] >= bot) or \
                           ((not bull) and H[i] >= bot and L[i] <= top):
                            poi = "fvg1h"
                            break
            if not poi:
                continue
            # aggressive return: close back beyond the swept low + same-direction FVG
            k_ok = -1
            back = False
            for k in range(i, min(n, i + 1 + RET_BARS)):
                back |= (C[k] > last) if bull else (C[k] < last)
                if k - 2 >= i and back:
                    if bull and L[k] > H[k - 2]:
                        k_ok, top, bot = k, L[k], H[k - 2]
                        break
                    if (not bull) and H[k] < L[k - 2]:
                        k_ok, top, bot = k, L[k - 2], H[k]
                        break
            if k_ok < 0:
                continue
            run_ext = L[i:k_ok + 1].min() if bull else H[i:k_ok + 1].max()
            ce = (top + bot) / 2.0
            end = ct[min(n - 1, k_ok + FILL_BARS)]
            m = _fill(mt, ML, MH, ct[k_ok], end, ce, bull, run_ext)
            if m is None:
                continue
            rows.append({"decision_time": mt[m] + 60 * NS, "direction": 1 if bull else -1,
                         "stop_px": float(run_ext), "poi": poi})
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows)
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True).dt.as_unit("ns")
    out["available_at"] = out["decision_time"]
    out["rr"] = RR
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)[cols]


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "anchor"]
    h = cl.build_bars(m1, "1h")
    if len(h) < 20:
        return pd.DataFrame(columns=cols)
    ev = cisd_events(h[["open", "high", "low", "close"]], level_rule="series_open",
                     left=SWING, right=SWING, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    hC = h["close"].to_numpy()
    hct = _ns(h["close_time"])
    pos_of = pd.Series(np.arange(len(h)), index=h.index)
    # anchors: hold one bias until its block is violated (1h close through the protected swing)
    # Bias = direction of the latest respected order block. A newer SAME-direction block
    # becomes the anchor (it is the block being respected now); opposite CISDs are ignored
    # while the bias holds ("I stick the one bias until I'm proven wrong"); the bias ends when
    # the current anchor block is violated (1h close through its protected swing).
    anchors = []                           # (bull, ps, t_on, t_end, id)
    cur = None                             # [bull, ps, t_on, t_off, id]
    for e in ev.itertuples(index=False):
        j0 = int(pos_of[e.confirm_time])
        t_on = hct[j0]
        bull = e.direction == "bullish"
        if cur is not None and t_on < cur[3] and bull != cur[0]:
            continue                       # opposite CISD while the bias holds: ignored
        ps = float(e.protected_swing)
        viol = np.flatnonzero((hC[j0 + 1:] < ps) if bull else (hC[j0 + 1:] > ps))
        t_off = hct[j0 + 1 + viol[0]] if len(viol) else np.iinfo(np.int64).max
        if cur is not None:
            anchors.append((cur[0], cur[1], cur[2], min(cur[3], t_on), cur[4]))
        cur = [bull, ps, t_on, t_off, str(e.confirm_time)]
    if cur is not None:
        anchors.append(tuple(cur))
    b = cl.build_bars(m1, TF)
    H, L = b["high"].to_numpy(), b["low"].to_numpy()
    ct = _ns(b["close_time"])
    n = len(b)
    mt = _ns(m1.index)
    ML, MH = m1["low"].to_numpy(), m1["high"].to_numpy()
    rows = []
    for (bull, ps, t_on, t_off, aid) in anchors:
        a = np.searchsorted(ct, t_on, side="right")      # 15m bars closing after the anchor
        for k in range(max(a, 2), n):
            if ct[k] >= t_off:
                break
            if int(np.searchsorted(ct, t_on, side="left")) > k - 2:
                continue                   # FVG must be formed entirely after the anchor
            if bull and L[k] > H[k - 2]:
                edge = L[k]
                if edge <= ps:
                    continue
            elif (not bull) and H[k] < L[k - 2]:
                edge = H[k]
                if edge >= ps:
                    continue
            else:
                continue
            end = min(ct[min(n - 1, k + FILL_BARS)], t_off)
            m = _fill(mt, ML, MH, ct[k], end, edge, bull, ps)
            if m is None:
                continue
            rows.append({"decision_time": mt[m] + 60 * NS, "direction": 1 if bull else -1,
                         "stop_px": ps, "anchor": aid})
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows)
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True).dt.as_unit("ns")
    # a fill before the anchor's violation close is valid only if the violation is later
    out["available_at"] = out["decision_time"]
    out["rr"] = RR
    return out.sort_values(["decision_time", "anchor"]).reset_index(drop=True)[cols]


def show(r):
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "ties", "exposure_bars"):
        print(" ", k, r.get(k))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    PARAMS = {"tf": TF, "swing": SWING, "ret_bars": RET_BARS, "fvg1h_life": FVG1H_LIFE,
              "fill_bars": FILL_BARS, "rr": RR, "max_hold": MAX_HOLD}
    SRC = {"tf": "corpus: concept htf 1H/15m, ltf 5m/1m; 15m execution with 1h POIs "
                 "(method_spec §1.2 rule 3)",
           "swing": "phase3: locked 2/2 swing",
           "ret_bars": "threshold_fits: displacement N-window N=4 (grade B); close-beyond hard gate (A)",
           "fvg1h_life": "declared-before-run: a 1h FVG is a live POI for 24 1h bars",
           "fill_bars": "declared-before-run: limit rests 12 entry-TF bars",
           "rr": "method_spec: §5.3 2R floor (examples show 2.6R and 4R)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    if "a" in which:
        ev = cl.cache_frame("tw_mss_a_15m", lambda: detect_a(cl.load_m1()))
        print("a", len(ev), ev["poi"].value_counts().to_dict())
        probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
        res = cl.trade_test(ev, max_hold=MAX_HOLD)
        print("reading a"); show(res)
        p = cl.write_result(
            "trading-without-structure-shift", "a", res,
            operationalization={"rules": [
                "15m: a bar sweeps the most recent unswept confirmed 2/2 swing low (short-term "
                "low run) while reaching a 1h POI: prior trading day low, or an active bullish "
                "1h FVG (formed <=24 1h bars ago, not closed through); mirrored for shorts",
                "aggressive return: within 4 bars a close back above the swept low and a "
                "bullish 15m FVG in the leg (no structure shift required)",
                "entry: limit at the FVG CE, resting 12 bars, cancelled if the run low trades "
                "first; decide at the touching M1 close, enter next M1 open",
                "stop = run low; target 2R; 150 min"], "params": {**PARAMS, "entry": "FVG CE"}},
            params_source={**SRC, "entry": "method_spec: §4.6 FVG CE is an accepted return "
                                          "level; fvg-entry-refinement (1) 'enter at the gap's 0.5'"},
            script=__file__, probe=probe,
            notes="Branch 2 (HTF POI run with no HTF close beyond -> OTE 0.62) not separately "
                  "tested; branch 1 is named 'the most important'.")
        print(p)
    if "b" in which:
        ev = cl.cache_frame("tw_mss_b2_15m", lambda: detect_b(cl.load_m1()))
        print("b", len(ev))
        probe = cl.probe_lookahead(detect_b, ev, lookback="30D")
        res = cl.trade_test(ev, max_hold=MAX_HOLD_B, cluster="anchor")
        print("reading b"); show(res)
        p = cl.write_result(
            "trading-without-structure-shift", "b", res,
            operationalization={"rules": [
                "bias = direction of the latest respected 1h CISD block (series_open, 2/2, within "
                "3 bars): a newer same-direction block replaces the anchor, opposite CISDs are "
                "ignored while the bias holds, and the bias ends on a 1h close through the "
                "current anchor's protected swing; the next CISD then sets the bias",
                "entry: first M1 touch of the near edge of a 15m FVG in the bias direction "
                "formed entirely after the anchor, within 12 bars and before the violation; "
                "no structure break used anywhere",
                "stop = the anchor's protected swing (bias proven wrong); 2R; 10h; "
                "cluster = anchor"], "params": {**PARAMS, "max_hold": MAX_HOLD_B, "entry": "FVG near edge",
                                                "anchor_tf": "1h", "cluster": "anchor"}},
            params_source={**SRC, "entry": "corpus: eK_6wgNpNh0 'the entry trigger is arrival "
                                           "at one of his four arrays, limit or market'",
                           "anchor_tf": "phase3: locked 1h CISD config as the order block",
                           "max_hold": "phase3: 10 bars of the 1h anchor TF (§1.13); the stop is "
                                       "1h structure, so 15m-bar holds would be time exits",
                           "cluster": "declared-before-run: trades sharing one bias anchor"},
            script=__file__, probe=probe,
            notes="Guest reading (Finessee_Fx). Of his four arrays only the FVG is used. "
                  "Pre-verdict fix: the first draft held the ORIGINAL block until violated, which "
                  "on this data kept one bullish anchor from 2016-01-04 for the whole decade "
                  "(gold never closed below it) and failed the lookahead probe; the anchor now "
                  "rolls to the latest same-direction block. No test had been run.")
        print(p)
