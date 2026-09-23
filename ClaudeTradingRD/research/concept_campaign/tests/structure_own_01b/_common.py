"""Shared, pure detector pieces for batch structure_own_01b (TTrades phases-of-price concepts).

Every function is a pure function of the M1 frame (or of bars built from it with
cl.build_bars), so probe_lookahead can re-run the detectors on truncated slices.

The phase layer is built from ONE mechanised object, the expansion event:

  expansion (threshold_fits §2, grade B; displacement == aggressive, one term)
    * a 2/2 fractal short-term high (low) is confirmed (right=2 bars later);
    * a later bar CLOSES beyond it (component (a): the hard close gate, no knob);
    * the N=4 window starting at that break bar has
        win_range / pre_range >= 1.5  and  dist_beyond_level / pre_range >= 0.65
      where pre_range is the range of the 4 bars before the break (component (b)).
    * decided at the close of the 4th window bar (break_pos + 3).
    * origin = the extreme "behind the move": for a bullish expansion the lowest low
      between the broken swing high and the break bar (mirror for bearish).

Everything else (reversal = expansion met with opposing expansion; continuation =
counter-move that does not become an opposing expansion) is read off the ordered
sequence of these events.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events              # noqa: E402
from detectors.primitives import swing_points       # noqa: E402

OHLC = ["open", "high", "low", "close"]
EXP_N, EXP_R, EXP_D = 4, 1.5, 0.65          # threshold_fits §2 defaults


def expansions(b: pd.DataFrame, n: int = EXP_N, r: float = EXP_R, d: float = EXP_D,
               left: int = 2, right: int = 2) -> pd.DataFrame:
    """Expansion events on bars `b` (built from M1). One row per fired break.

    columns: dir (+1/-1), sw_pos, break_pos, dec_pos, dec_time (close_time of dec bar),
    level (broken swing), origin, origin_pos, win_ext (window extreme in dir).
    """
    cols = ["dir", "sw_pos", "break_pos", "dec_pos", "dec_time", "level", "origin",
            "origin_pos", "win_ext"]
    nb = len(b)
    if nb < left + right + 2 * n + 2:
        return pd.DataFrame(columns=cols)
    sp = swing_points(b[OHLC], left, right)
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    ct = b["close_time"].to_numpy()
    sh = np.flatnonzero(sp["swing_high"].to_numpy())
    sl = np.flatnonzero(sp["swing_low"].to_numpy())
    rows = []
    for side, piv in ((1, sh), (-1, sl)):
        # the live level at bar i = most recent swing confirmed (pos+right) <= i-1
        conf = piv + right
        used = set()
        for i in range(left + right + 1, nb - n + 1):
            k = np.searchsorted(conf, i - 1, side="right") - 1
            if k < 0:
                continue
            p = int(piv[k])
            if p in used:
                continue
            lvl = h[p] if side == 1 else l[p]
            broke = c[i] > lvl if side == 1 else c[i] < lvl
            if not broke:
                continue
            used.add(p)
            if i + n - 1 >= nb:
                continue
            w = slice(i, i + n)
            pre = slice(max(0, i - n), i)
            pre_range = h[pre].max() - l[pre].min()
            if not pre_range > 0:
                continue
            win_range = h[w].max() - l[w].min()
            dist = (h[w].max() - lvl) if side == 1 else (lvl - l[w].min())
            if win_range / pre_range >= r and dist / pre_range >= d:
                seg = slice(p, i + 1)
                if side == 1:
                    op = p + int(np.argmin(l[seg]))
                    org = l[op]
                    wext = h[w].max()
                else:
                    op = p + int(np.argmax(h[seg]))
                    org = h[op]
                    wext = l[w].min()
                rows.append({"dir": side, "sw_pos": p, "break_pos": i,
                             "dec_pos": i + n - 1, "dec_time": ct[i + n - 1],
                             "level": float(lvl), "origin": float(org), "origin_pos": op,
                             "win_ext": float(wext)})
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows)
    out["dec_time"] = pd.DatetimeIndex(out["dec_time"])
    return out.sort_values(["dec_pos", "break_pos", "dir"]).reset_index(drop=True)


def cisd15(m1: pd.DataFrame, tf: str = "15min", level_rule: str = "series_open",
           max_wait: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Phase-3 rung-0 CISD events (2/2 swing, min_series 1) with positional indices."""
    b = cl.build_bars(m1, tf)
    cols = ["direction", "ext_pos", "conf_pos", "s_pos", "e_pos", "close_time",
            "protected_swing", "d"]
    if len(b) < 10:
        return b, pd.DataFrame(columns=cols)
    ev = cisd_events(b[OHLC], level_rule=level_rule, left=2, right=2, max_wait=max_wait,
                     min_series=1)
    if ev.empty:
        return b, pd.DataFrame(columns=cols)
    ev = ev.copy()
    ev["ext_pos"] = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    ev["conf_pos"] = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    ev["s_pos"] = b.index.get_indexer(pd.DatetimeIndex(ev["series_start"]))
    ev["e_pos"] = b.index.get_indexer(pd.DatetimeIndex(ev["series_end"]))
    ev["close_time"] = pd.DatetimeIndex(b["close_time"].to_numpy()[ev["conf_pos"].to_numpy()])
    ev["d"] = np.where(ev["direction"].to_numpy() == "bullish", 1, -1)
    return b, ev.reset_index(drop=True)


def latest_idx(dec_times: pd.DatetimeIndex, t) -> np.ndarray:
    """Index of the latest event with dec_time <= t (-1 if none)."""
    a = np.asarray(pd.DatetimeIndex(dec_times).as_unit("ns").asi8)
    q = np.asarray(pd.DatetimeIndex(t).as_unit("ns").asi8)
    return np.searchsorted(a, q, side="right") - 1


def continuation_context(b15: pd.DataFrame, ev: pd.DataFrame, b1h: pd.DataFrame,
                         ex: pd.DataFrame) -> pd.DataFrame:
    """For each 15m CISD event: the latest 1h expansion (dec_time <= decision), and the
    leg geometry measured on 15m bars up to the extreme bar.

    Returns per-event columns: e_idx, e_dir, aligned, H (leg extreme before the pullback,
    from the expansion's break bar to the extreme bar), tH, O (origin), tO, L (the CISD
    extreme), tL, depth ((H-L)/(H-O) in trend units), h_after (extreme reached between
    the CISD extreme and its confirmation, in the trend direction), exp_before_ext.
    """
    n = len(ev)
    out = pd.DataFrame(index=ev.index)
    if n == 0 or ex.empty:
        for c in ("e_idx", "e_dir", "aligned", "H", "tH", "O", "tO", "L", "tL", "depth",
                  "h_after", "exp_before_ext"):
            out[c] = pd.Series(dtype="float64")
        return out
    t = pd.DatetimeIndex(ev["close_time"])
    ei = latest_idx(pd.DatetimeIndex(ex["dec_time"]), t)
    d = ev["d"].to_numpy()
    h15, l15 = b15["high"].to_numpy(), b15["low"].to_numpy()
    st15 = b15.index.as_unit("ns").asi8
    ct15 = pd.DatetimeIndex(b15["close_time"]).as_unit("ns").asi8
    st1h = b1h.index.as_unit("ns").asi8
    ext_pos = ev["ext_pos"].to_numpy()
    conf_pos = ev["conf_pos"].to_numpy()
    E_dir = ex["dir"].to_numpy()
    E_brk = ex["break_pos"].to_numpy()
    E_org = ex["origin"].to_numpy()
    E_orgp = ex["origin_pos"].to_numpy()
    E_dec_ns = pd.DatetimeIndex(ex["dec_time"]).as_unit("ns").asi8
    res = {k: np.full(n, np.nan) for k in ("e_dir", "H", "tH", "O", "tO", "L", "tL",
                                           "depth", "h_after")}
    aligned = np.zeros(n, bool)
    before = np.zeros(n, bool)
    for k in range(n):
        j = ei[k]
        if j < 0:
            continue
        res["e_dir"][k] = E_dir[j]
        aligned[k] = E_dir[j] == d[k]
        # the pullback extreme must print after the expansion was decided
        before[k] = E_dec_ns[j] <= st15[ext_pos[k]]
        # 15m bar range from the expansion's 1h break bar start to the extreme bar
        a = np.searchsorted(st15, st1h[E_brk[j]], side="left")
        e = ext_pos[k]
        if a > e:
            continue
        if d[k] == 1:
            seg = h15[a:e + 1]
            hp = a + int(np.argmax(seg))
            H = seg.max()
            L = l15[e]
            O = E_org[j]
            depth = (H - L) / (H - O) if H > O else np.nan
            after = h15[e:conf_pos[k] + 1].max()
        else:
            seg = l15[a:e + 1]
            hp = a + int(np.argmin(seg))
            H = seg.min()
            L = h15[e]
            O = E_org[j]
            depth = (L - H) / (O - H) if O > H else np.nan
            after = l15[e:conf_pos[k] + 1].min()
        res["H"][k] = H
        res["tH"][k] = ct15[hp]                        # the leg extreme's bar close
        res["O"][k] = O
        res["tO"][k] = pd.Timestamp(b1h["close_time"].iloc[E_orgp[j]]).value
        res["L"][k] = L
        res["tL"][k] = ct15[e]
        res["depth"][k] = depth
        res["h_after"][k] = after
    out["e_idx"] = ei
    for kk, v in res.items():
        out[kk] = v
    out["aligned"] = aligned
    out["exp_before_ext"] = before
    return out


def empty_frame(cols, extra_bool=(), extra_float=()) -> pd.DataFrame:
    out = pd.DataFrame({c: pd.Series(dtype="float64") for c in cols})
    for c in ("decision_time", "available_at"):
        if c in cols:
            out[c] = pd.Series(dtype="datetime64[ns, UTC]")
    for c in extra_bool:
        out[c] = pd.Series(dtype=bool)
    for c in extra_float:
        out[c] = pd.Series(dtype="float64")
    return out


def show(res: dict) -> None:
    for k in ("test_type", "n", "n_gated", "n_complement", "avg_R", "observed_rate",
              "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "gate_rate",
              "dropped"):
        if k in res and res.get(k) is not None:
            print(f"  {k:15s} {res[k]}")
