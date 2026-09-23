"""The three test types. Each returns ONE flat, JSON-able dict (the result schema in
`results.py`) whose verdict comes from the LOCKED `rules.verdict`.

    trade_test(events, max_hold=...)            does this entry rule beat random entry?
    gate_test(events, mask, mask_available_at)  does this filter improve a baseline book?
    rate_test(observed, times, available_at, null_fn|null|null_p)
                                                does this prediction beat a matched null?

Statistics reuse phase 3 verbatim: `backtest_conjunction.diff_with_ci` (the WIDER
of an i.i.d. bootstrap and a paired stationary block bootstrap, mean block 20),
`_block_boot`, `calendar_blocks`, `sanity_flags`; the control window (+/-30 days),
K=5 reps, seed, 2,000 draws and the 0.04R cost are imported constants.

rules-2 (review of 2026-09-23) adds, for every test type:
  * a stationary bootstrap over TRADING-DAY buckets (mean block = the book's own
    dependence length in days) and, if declared, over explicit clusters; the
    reported CI is the WIDEST of all components (`ci_components` lists each), and
    the effective n (days / clusters) must reach N_MIN_EDGE;
  * trade/gate: tie diagnostics and the 50/50 re-scoring robustness rule, the
    control-overlap share, and a fingerprint of the input frame (`events_fp`)
    that write_result matches against the lookahead probe;
  * every call is appended to the campaign run ledger (`run_id`), which
    `adjust_campaign` counts, so unwritten readings still enter the multiplicity.

Everything is sorted by decision time before any bootstrap — the block bootstrap
is only meaningful on a time-ordered series.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time as _time
import uuid

import numpy as np
import pandas as pd

from backtest_conjunction import (diff_with_ci, _block_boot, calendar_blocks,
                                  sanity_flags)
from backtest_c2_wick import boot_diff
from . import rules
from .rules import (CTRL_REPS, CTRL_WINDOW_DAYS, SEED, N_BOOT, PRIMARY_COST,
                    SPLIT_DATE, mde_from_ci, p_from_ci, power_floor_n,
                    resolve_threshold, verdict)
from .engine import get_market, resolve_trades, sample_times
from .lookahead import assert_no_lookahead, LookaheadError, frame_fingerprint
from .data import bars as _bars, utc_ns, from_ns, trading_day, CAMPAIGN_DIR

_DIR_STR = {"bullish": 1, "bearish": -1, "long": 1, "short": -1, "buy": 1, "sell": -1,
            "bull": 1, "bear": -1}
LEDGER = os.environ.get("CONCEPT_LAB_LEDGER", str(CAMPAIGN_DIR / "ledger.jsonl"))
ENTRY_MODES = ("next_open", "prev_close")
HOLD_BASES = ("clock", "bars")


# ══ shared helpers ════════════════════════════════════════════════════════════
def _utc(x) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(x)
    if idx.tz is None:
        raise ValueError("timestamps must be tz-aware (UTC)")
    return idx.tz_convert("UTC").as_unit("ns")


def _direction(s) -> np.ndarray:
    """+1/-1 (int or float), or bullish/bearish/long/short/buy/sell/bull/bear.

    Everything else RAISES: 0 / NaN ("no signal" must be dropped, not traded) and
    booleans (True/False hash like 1/0, which once turned direction 0 into SHORT)."""
    ser = pd.Series(s)
    if len(ser) == 0:
        return np.zeros(0, int)
    if ser.dtype == bool:
        raise ValueError("direction must be +1/-1 (or bullish/bearish), not booleans")
    if ser.dtype.kind in "iuf":
        v = ser.to_numpy(float)
        bad = ~np.isin(v, (1.0, -1.0))
        if bad.any():
            raise ValueError(f"direction must be +1/-1; {int(bad.sum())} rows are "
                             f"{sorted(set(map(str, v[bad][:5])))} — drop no-signal rows")
        return v.astype(int)
    out = np.zeros(len(ser), int)
    for i, v in enumerate(ser.to_numpy(object)):
        if isinstance(v, (bool, np.bool_)):
            raise ValueError("direction must be +1/-1 (or bullish/bearish), not booleans")
        if isinstance(v, str) and v.strip().lower() in _DIR_STR:
            out[i] = _DIR_STR[v.strip().lower()]
        elif isinstance(v, (int, float, np.integer, np.floating)) and float(v) in (1.0, -1.0):
            out[i] = int(v)
        else:
            raise ValueError(f"direction must be +1/-1 (or bullish/bearish): got {v!r}")
    return out


def _f(x):
    """JSON-safe float."""
    if x is None:
        return None
    x = float(x)
    return x if np.isfinite(x) else None


def _pair_ci(a_pooled, b_pooled, a_pair, b_pair, n_boot, seed):
    d, lo, hi, how = diff_with_ci(np.asarray(a_pooled, float), np.asarray(b_pooled, float),
                                  np.asarray(a_pair, float), np.asarray(b_pair, float),
                                  n_boot=n_boot, seed=seed)
    return float(d), float(lo), float(hi), how


def _two_group_ci(g: np.ndarray, c: np.ndarray, n_boot: int, seed: int):
    """CI on mean(g) - mean(c) for two INDEPENDENT time-ordered groups: the wider
    of i.i.d. and per-group stationary block bootstrap (as `Book.rise`)."""
    if len(g) < 2 or len(c) < 2:
        return np.nan, np.nan, np.nan, "n/a"
    obs, lo_i, hi_i = boot_diff(g, c, n=n_boot, seed=seed)
    (mg,) = _block_boot([g], n_boot, np.random.default_rng(seed + 3))
    (mc,) = _block_boot([c], n_boot, np.random.default_rng(seed + 4))
    d = mg - mc
    lo_b, hi_b = float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
    if (hi_b - lo_b) > (hi_i - lo_i):
        return float(obs), lo_b, hi_b, "block"
    return float(obs), float(lo_i), float(hi_i), "iid"


def _cell(t: pd.DatetimeIndex, sel: np.ndarray, fn) -> dict:
    n = int(sel.sum())
    out = {"n": n}
    if n >= 2:
        d, lo, hi, how = fn(sel)
        out.update(diff=_f(d), ci_lo=_f(lo), ci_hi=_f(hi), ci_method=how,
                   p=_f(p_from_ci(d, lo, hi)))
    if n:
        out.update(start=str(t[sel].min()), end=str(t[sel].max()))
    return out


def _halves_blocks(t: pd.DatetimeIndex, fn, m1, split=SPLIT_DATE, blocks=True) -> tuple:
    tn = utc_ns(t)
    sp = np.datetime64(pd.Timestamp(split).tz_convert("UTC").tz_localize(None), "ns")
    halves = {"H1": _cell(t, tn < sp, fn), "H2": _cell(t, tn >= sp, fn),
              "split": str(split)}
    blk = {}
    if blocks:
        mk = get_market(m1)
        for name, a, b in calendar_blocks(mk.m1):
            a_ = np.datetime64(a.tz_convert("UTC").tz_localize(None), "ns")
            b_ = np.datetime64(b.tz_convert("UTC").tz_localize(None), "ns")
            sel = (tn >= a_) & ((tn < b_) if name != "B4" else np.ones(len(tn), bool))
            c = _cell(t, sel, fn)
            c.update(block_start=str(a), block_end=str(b))
            blk[name] = c
    return halves, blk


def _book_stats(r: np.ndarray, reason: np.ndarray | None = None) -> dict:
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n == 0:
        return {"n": 0, "avg_R": None, "win_rate": None, "pf": None}
    pos, neg = r[r > 0].sum(), -r[r <= 0].sum()
    out = {"n": n, "avg_R": _f(r.mean()), "win_rate": _f((r > 0).mean()),
           "pf": _f(pos / neg) if neg > 0 else None, "sd_R": _f(r.std(ddof=1)) if n > 1 else None}
    if reason is not None:
        out["exit_mix"] = {"stop": _f((reason == 0).mean()), "target": _f((reason == 1).mean()),
                           "time": _f((reason == 2).mean())}
    return out


def _cost_r(gross_r: np.ndarray, risk: np.ndarray, cost) -> np.ndarray:
    if isinstance(cost, str) and cost.endswith("R"):
        return gross_r - float(cost[:-1])
    return gross_r - float(cost) / risk


# ══ dependence-aware CIs (rules-2) ════════════════════════════════════════════
_DAY_NS = np.int64(86_400 * 10 ** 9)


def _codes(values) -> np.ndarray:
    """Integer bucket codes in order of first appearance (rows are time-sorted, so
    codes are chronological)."""
    codes, _ = pd.factorize(pd.Series(np.asarray(values)), use_na_sentinel=False)
    return codes.astype(np.int64)


def _day_codes(t: pd.DatetimeIndex) -> np.ndarray:
    return _codes(np.asarray(trading_day(t)))


def _dep_days(tn: np.ndarray, sgn: np.ndarray, hold_ns: np.ndarray) -> int:
    """Dependence length of a book in trading days: max_hold plus the length of the
    same-direction run of overlapping trades a trade sits in (the 90th percentile
    over trades), rounded up to whole days, at least 1."""
    n = len(tn)
    if n == 0:
        return 1
    t = tn.astype("datetime64[ns]").astype(np.int64)
    h = hold_ns.astype("timedelta64[ns]").astype(np.int64)
    new = np.r_[True, (sgn[1:] != sgn[:-1]) | ((t[1:] - t[:-1]) > h[:-1])]
    rid = np.cumsum(new) - 1
    start = t[new]
    end = np.full(rid[-1] + 1, np.iinfo(np.int64).min)
    np.maximum.at(end, rid, t + h)
    dur = (end - start)[rid]
    q = float(np.quantile(dur, rules.DAY_BLOCK_RUN_QUANTILE))
    return int(max(1, math.ceil(q / _DAY_NS)))


def _bucket_ci(codes: np.ndarray, arrays: list, stat, n_boot: int, seed: int,
               mean_block: float) -> tuple[float, float]:
    """Percentile CI of stat(*bucket-sum means) under a stationary bootstrap over
    the bucket series (buckets = trading days or declared clusters, in time order).
    Ratio estimators (sums / counts) keep unequal bucket sizes honest."""
    if len(codes) == 0:
        return np.nan, np.nan
    nb = int(codes.max()) + 1
    if nb < 2:
        return np.nan, np.nan
    sums = [np.bincount(codes, weights=np.asarray(a, float), minlength=nb) for a in arrays]
    draws = _block_boot(sums, n_boot, np.random.default_rng(seed), mean_block=mean_block)
    with np.errstate(invalid="ignore", divide="ignore"):
        v = stat(*draws)
    v = v[np.isfinite(v)]
    if len(v) < max(20, n_boot // 2):
        return np.nan, np.nan
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def _widest(obs: float, comps: dict) -> tuple[float, float, str]:
    best, how = None, "n/a"
    for k, (lo, hi) in comps.items():
        if lo is None or hi is None or not (np.isfinite(lo) and np.isfinite(hi)):
            continue
        if best is None or (hi - lo) > (best[1] - best[0]):
            best, how = (lo, hi), k
    if best is None:
        return np.nan, np.nan, "n/a"
    return best[0], best[1], how


def _cluster_arg(cluster, frame: pd.DataFrame | None, n: int):
    """cluster: None, a column name of `frame`, or an array of per-row ids."""
    if cluster is None:
        return None, None
    if isinstance(cluster, str):
        if frame is None or cluster not in frame.columns:
            raise ValueError(f"cluster column {cluster!r} not in the events frame")
        vals = frame[cluster].to_numpy()
        desc = f"column:{cluster}"
    else:
        vals = np.asarray(cluster)
        desc = "array"
    if len(vals) != n:
        raise ValueError("cluster length != number of rows")
    if pd.isna(pd.Series(vals)).any():
        raise ValueError("cluster ids contain NaN")
    return vals, desc


# ══ run ledger (rules-2): every test call is logged, so readings that are never
# written still count in the campaign's multiplicity (adjust_campaign) ══════════
_HYP_EXCLUDE = ("seed", "n_boot", "blocks", "keep_trades")


def _hyp_key(test_type: str, claim, fps: tuple, settings: dict) -> str:
    st = {k: v for k, v in settings.items() if k not in _HYP_EXCLUDE}
    raw = json.dumps([test_type, claim, list(fps), st], sort_keys=True, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _ledger(out: dict, fps: tuple) -> None:
    out["run_id"] = None
    out["hyp_key"] = _hyp_key(out.get("test_type"), out.get("claim"), fps,
                              out.get("settings") or {})
    if os.environ.get("CONCEPT_LAB_LEDGER_DISABLE"):
        return
    path = os.environ.get("CONCEPT_LAB_LEDGER", LEDGER)
    rid = uuid.uuid4().hex
    rec = {"run_id": rid, "hyp_key": out["hyp_key"], "time": _time.time(),
           "pid": os.getpid(), "script": os.path.abspath(sys.argv[0]) if sys.argv and
           sys.argv[0] else None, "test_type": out.get("test_type"),
           "claim": out.get("claim"), "n": out.get("n"), "diff": out.get("diff"),
           "ci_lo": out.get("ci_lo"), "ci_hi": out.get("ci_hi"), "p": out.get("p"),
           "verdict": out.get("verdict"), "fps": list(fps),
           "seed": (out.get("settings") or {}).get("seed")}
    line = (json.dumps(rec, default=str) + "\n").encode()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line)                  # one O_APPEND write per record
    finally:
        os.close(fd)
    out["run_id"] = rid


# ══ book construction ═════════════════════════════════════════════════════════
def _prepare(events: pd.DataFrame, max_hold) -> pd.DataFrame:
    need = {"decision_time", "direction", "available_at"}
    miss = need - set(events.columns)
    if miss:
        raise ValueError(f"events missing columns {sorted(miss)} (available_at = latest "
                         f"close_time of every bar/level the rule used)")
    if not ({"stop_px", "stop_dist"} & set(events.columns)):
        raise ValueError("events need stop_px or stop_dist")
    tcols = [c for c in ("target_px", "rr", "target_dist") if c in events.columns]
    if len(tcols) != 1:
        raise ValueError("events need exactly one of target_px / rr / target_dist "
                         "(NaN in a row = no target: stop or time exit)")
    ev = events.copy()
    ev["ev_id"] = np.arange(len(ev))
    ev["decision_time"] = _utc(ev["decision_time"])
    ev["available_at"] = _utc(ev["available_at"])
    ev["_sgn"] = _direction(ev["direction"])
    if "max_hold" in ev.columns:
        ev["_hold"] = pd.to_timedelta(ev["max_hold"])
    elif max_hold is not None:
        ev["_hold"] = pd.Timedelta(max_hold)
    else:
        raise ValueError("declare max_hold (param or column) — no default, by design")
    if ev["_hold"].isna().any():
        raise ValueError(f"max_hold is NaT/NaN on {int(ev['_hold'].isna().sum())} rows — "
                         f"a missing hold would run to the end of the data")
    if (ev["_hold"] <= pd.Timedelta(0)).any():
        raise ValueError("max_hold must be positive")
    ev.attrs["target_col"] = tcols[0]
    return ev.sort_values(["decision_time", "ev_id"], kind="stable").reset_index(drop=True)


def _build_book(ev: pd.DataFrame, mkt, entry_mode: str, reps: int, window_days: float,
                ctrl_grid, align, tod_tol_min, seed: int, cost, m1,
                hold_basis: str = "clock") -> dict:
    if entry_mode not in ENTRY_MODES:
        raise ValueError(f"entry_mode must be one of {ENTRY_MODES}")
    if hold_basis not in HOLD_BASES:
        raise ValueError(f"hold_basis must be one of {HOLD_BASES}")
    n_in = len(ev)
    N = len(mkt.tn)
    d = pd.DatetimeIndex(ev["decision_time"])
    sgn = ev["_sgn"].to_numpy()
    hold = pd.to_timedelta(ev["_hold"]).to_numpy()
    i0 = np.searchsorted(mkt.tn, utc_ns(d), side="left")
    drop = {}
    ok = i0 < N
    if entry_mode == "prev_close":
        ok &= i0 > 0
    drop["no_bar_after_decision"] = int((~ok).sum())
    i0c = np.clip(i0, 1 if entry_mode == "prev_close" else 0, N - 1)
    entry = mkt.o[i0c] if entry_mode == "next_open" else mkt.c[i0c - 1]
    if "stop_px" in ev.columns:
        stop = ev["stop_px"].to_numpy(float)
        risk = sgn * (entry - stop)
    else:
        risk = ev["stop_dist"].to_numpy(float)
        stop = entry - sgn * risk
    bad = ok & ~(np.isfinite(risk) & (risk > 0))
    drop["stop_not_beyond_entry"] = int(bad.sum())
    ok &= ~bad
    tc = ev.attrs["target_col"]
    tv = ev[tc].to_numpy(float)
    if tc == "rr":
        tgt = entry + sgn * tv * risk
    elif tc == "target_dist":
        tgt = entry + sgn * tv
    else:
        tgt = tv
    tdist = sgn * (tgt - entry)
    bad = ok & np.isfinite(tgt) & ~(tdist > 0)
    drop["target_not_beyond_entry"] = int(bad.sum())
    ok &= ~bad
    hold_bars = (hold.astype("timedelta64[ns]") // np.timedelta64(1, "m")).astype(np.int64)
    if hold_basis == "clock":        # phase-3 §1.13: wall clock from the decision
        i1 = np.searchsorted(mkt.tn, utc_ns(d) + hold.astype("timedelta64[ns]"), side="left")
    else:                            # trading time: the same number of M1 bars
        i1 = np.minimum(i0 + hold_bars, N)
    bad = ok & ~(i1 > i0)
    drop["no_bars_in_hold"] = int(bad.sum())
    ok &= ~bad

    ev = ev[ok].reset_index(drop=True)
    i0, i1, entry, stop, tgt, risk, tdist, sgn, hold, hold_bars = (
        a[ok] for a in (i0, i1, entry, stop, tgt, risk, tdist, sgn, hold, hold_bars))
    n = len(ev)
    d = pd.DatetimeIndex(ev["decision_time"])
    entry_time = from_ns(mkt.tn[i0])
    look = assert_no_lookahead(d, ev["available_at"], "events", entry_time=entry_time)
    # the harness's own convention, asserted rather than assumed (trap 3)
    if n and not (mkt.tn[i0] >= utc_ns(d)).all():
        raise LookaheadError("entry bar starts before the decision time")

    # ── matched control: same direction, stop distance, target distance, hold ──
    grid_times = None
    if isinstance(ctrl_grid, str) and ctrl_grid not in ("m1", "auto"):
        grid_times = _bars(ctrl_grid, m1=m1)["close_time"]
    ct = sample_times(d, reps, window_days, seed, align=align, tod_tol_min=tod_tol_min,
                      grid_times=grid_times, m1=m1) if n else np.empty((0, reps), "datetime64[ns]")
    ctf = ct.T.reshape(-1)                                  # rep-major
    src = np.tile(np.arange(n), reps)
    has = ~np.isnat(ctf)
    ci0 = np.searchsorted(mkt.tn, ctf, side="left")
    cok = has & (ci0 < N) & ((ci0 > 0) if entry_mode == "prev_close" else True)
    ci0c = np.clip(ci0, 1 if entry_mode == "prev_close" else 0, N - 1)
    centry = mkt.o[ci0c] if entry_mode == "next_open" else mkt.c[ci0c - 1]
    cs = sgn[src]
    cstop = centry - cs * risk[src]
    ctgt = np.where(np.isfinite(tgt[src]), centry + cs * tdist[src], np.nan)
    if hold_basis == "clock":
        ci1 = np.searchsorted(mkt.tn, np.where(has, ctf, mkt.tn[0]) +
                              hold[src].astype("timedelta64[ns]"), side="left")
    else:
        ci1 = np.minimum(ci0 + hold_bars[src], N)
    cok &= ci1 > ci0
    csrc, cent, cst, ctg, ci0, ci1 = (a[cok] for a in (src, centry, cstop, ctgt, ci0, ci1))

    # ── resolve both arms in one pass ──
    allL = np.concatenate([sgn > 0, sgn[csrc] > 0])
    res = resolve_trades(mkt, allL, np.concatenate([stop, cst]), np.concatenate([tgt, ctg]),
                         np.concatenate([i0, ci0]), np.concatenate([i1, ci1]))
    ent = np.concatenate([entry, cent])
    rk = np.concatenate([risk, risk[csrc]])
    ss = np.concatenate([sgn, sgn[csrc]])
    gross = ss * (res["exit_px"] - ent) / rk
    net = _cost_r(gross, rk, cost)
    rr_, cr = net[:n], net[n:]
    reason = res["reason"]
    # rules-2: the same book with every AMBIGUOUS same-bar stop+target exit scored
    # as a coin flip (and bars that opened through the target as the target)
    alltg = np.concatenate([tgt, ctg])
    r_tgt = ss * (alltg - ent) / rk
    r_stp = ss * (np.concatenate([stop, cst]) - ent) / rk
    g5050 = np.where(res["ambiguous"], 0.5 * r_stp + 0.5 * r_tgt,
                     np.where(res["open_tgt"], r_tgt, gross))
    net5050 = _cost_r(g5050, rk, cost)
    tie = res["ambiguous"] | res["open_tgt"]
    # per-real-trade control mean (for the paired block bootstrap)
    cnt = np.bincount(csrc, minlength=n)

    def _pmean(v):
        o = np.full(n, np.nan)
        s_ = np.bincount(csrc, weights=v, minlength=n)
        o[cnt > 0] = s_[cnt > 0] / cnt[cnt > 0]
        return o
    cm = _pmean(cr)
    cm5050 = _pmean(net5050[n:])
    # rules-2: control draws that ARE one of the concept's own trades (same entry
    # bar, same direction) — the differential is attenuated by roughly that share
    rk_real = i0.astype(np.int64) * 2 + (sgn > 0)
    rk_ctrl = ci0.astype(np.int64) * 2 + (sgn[csrc] > 0)
    overlap = float(np.isin(rk_ctrl, rk_real).mean()) if len(rk_ctrl) else None
    cw = np.full(n, np.nan)
    sw = np.bincount(csrc, weights=(cr > 0).astype(float), minlength=n)
    cw[cnt > 0] = sw[cnt > 0] / cnt[cnt > 0]

    trades = pd.DataFrame({
        "ev_id": ev["ev_id"].to_numpy(), "decision_time": d, "entry_time": entry_time,
        "direction": sgn, "entry": entry, "stop": stop, "target": tgt, "risk": risk,
        "exit_time": from_ns(mkt.tn[res["exit_pos"][:n]]),
        "exit_px": res["exit_px"][:n], "reason": np.array(["stop", "target", "time"])[reason[:n]],
        "gross_R": gross[:n], "net_R": rr_, "ctrl_mean_R": cm, "ctrl_win": cw,
        "ctrl_n": cnt})
    trades["net_R_5050"] = net5050[:n]
    trades["ctrl_mean_R_5050"] = cm5050
    trades["tie"] = tie[:n]
    return {"n_in": n_in, "drop": drop, "trades": trades, "ctrl_r": cr,
            "ctrl_r_5050": net5050[n:], "ctrl_tie": tie[n:], "ctrl_src": csrc,
            "ties": {"real_ambiguous": _f(tie[:n].mean()) if n else None,
                     "control_ambiguous": _f(tie[n:].mean()) if len(tie) > n else None,
                     "real_gap_stop": _f(res["gap_stop"][:n].mean()) if n else None,
                     "control_gap_stop": _f(res["gap_stop"][n:].mean())
                     if len(tie) > n else None},
            "ctrl_overlap": _f(overlap) if overlap is not None else None,
            "hold_ns": hold.astype("timedelta64[ns]"),
            "ctrl_reason": reason[n:], "ctrl_gross": gross[n:], "reason": reason[:n],
            "ctrl_fill": float(cok.sum() / max(1, n * reps)), "lookahead": look,
            # tradable M1 bars inside the hold window, real vs control: a gap here
            # means the two arms had different EXPOSURE (halts/weekends), which a
            # time-exit-heavy book turns into a spurious differential
            "exposure_bars": {"real_mean": _f(np.mean(i1 - i0)) if n else None,
                              "control_mean": _f(np.mean(ci1 - ci0)) if len(ci0) else None,
                              "hold_basis": hold_basis},
            "entry_delay_min": {
                "median": _f(np.median((entry_time - d).total_seconds() / 60)) if n else None,
                "max": _f(((entry_time - d).total_seconds() / 60).max()) if n else None}}


def _settings(**kw) -> dict:
    out = {}
    for k, v in kw.items():
        out[k] = str(v) if isinstance(v, (pd.Timedelta, pd.Timestamp)) else v
    return out


# ══ shared statistic cores ════════════════════════════════════════════════════
def _paired_core(t, real_r, ctrl_r, cm, good, day_codes, clu_codes, dep, n_boot, seed,
                 m1, split, blocks):
    """diff = mean(real) - mean(control) with every CI component; halves/blocks."""
    d, lo_p, hi_p, how_p = _pair_ci(real_r, ctrl_r, real_r[good], cm[good], n_boot, seed)
    comps = {f"phase3_{how_p}": (lo_p, hi_p)}
    ones = np.ones(int(good.sum()))
    stat = (lambda a, b, c: (a - b) / c)
    comps["day_block"] = _bucket_ci(day_codes, [real_r[good], cm[good], ones], stat,
                                    n_boot, seed + 11, dep)
    if clu_codes is not None:
        comps["cluster"] = _bucket_ci(clu_codes, [real_r[good], cm[good], ones], stat,
                                      n_boot, seed + 13, 1)
    lo, hi, how = _widest(d, comps)

    def fn(sel):
        s_ = sel & good
        return _pair_ci(real_r[s_], cm[s_], real_r[s_], cm[s_], max(500, n_boot // 2),
                        seed + 17)
    halves, blk = _halves_blocks(t, fn, m1, split, blocks)
    return d, lo, hi, how, comps, halves, blk


def _gate_core(t, adj, g, c, day_codes, clu_codes, dep, n_boot, seed, m1, split, blocks):
    d, lo_p, hi_p, how_p = _two_group_ci(adj[g], adj[c], n_boot, seed)
    comps = {f"phase3_{how_p}": (lo_p, hi_p)}
    good = g | c
    a = np.where(g, adj, 0.0)[good]
    b = np.where(c, adj, 0.0)[good]
    stat = (lambda sa, ng, sb, nc: sa / ng - sb / nc)
    arrs = [a, g[good].astype(float), b, c[good].astype(float)]
    comps["day_block"] = _bucket_ci(day_codes, arrs, stat, n_boot, seed + 11, dep)
    if clu_codes is not None:
        comps["cluster"] = _bucket_ci(clu_codes, arrs, stat, n_boot, seed + 13, 1)
    lo, hi, how = _widest(d, comps)

    def fn_ok(sel):
        if (sel & g).sum() < 2 or (sel & c).sum() < 2:
            return np.nan, np.nan, np.nan, "n/a"
        return _two_group_ci(adj[sel & g], adj[sel & c], max(500, n_boot // 2), seed + 17)
    halves, blk = _halves_blocks(t, fn_ok, m1, split, blocks)
    return d, lo, hi, how, comps, halves, blk


def _comps_json(comps: dict) -> dict:
    return {k: [_f(v[0]), _f(v[1])] for k, v in comps.items()}


# ══ trade_test ════════════════════════════════════════════════════════════════
def trade_test(events: pd.DataFrame, *, max_hold=None, claim: str = "+",
               cost=PRIMARY_COST, reps: int = CTRL_REPS,
               window_days: float = CTRL_WINDOW_DAYS, ctrl_grid="auto",
               ctrl_tod_tol_min: int | None = None, mde_threshold: float | None = None,
               entry_mode: str = "next_open", hold_basis: str = "clock",
               cluster=None, n_boot: int = N_BOOT, seed: int = SEED,
               split=SPLIT_DATE, blocks: bool = True, keep_trades: bool = False,
               m1: pd.DataFrame | None = None) -> dict:
    """Does this entry rule beat a matched random entry?

    events columns:
      decision_time  UTC; the moment the rule has decided (>= close of every input bar)
      available_at   UTC; the latest close_time/available_at of anything the rule read
      direction      +1 long / -1 short (0, NaN and booleans raise — drop no-signal rows)
      stop_px | stop_dist        stop level, or distance from the entry price
      target_px | rr | target_dist   target level, R-multiple, or distance (NaN: none)
      max_hold (optional column) else the `max_hold` param (e.g. "10h") — measured
                     from decision_time; no default, you must declare it; NaT raises
    Entry is the OPEN of the first M1 bar starting at/after decision_time
    (`entry_mode="prev_close"` exists only to reproduce phase-3 books, which
    entered at the signal close; write_result refuses it). Exits resolve on M1,
    stop-first ties.
    hold_basis: "clock" (default; phase-3 §1.13 — max_hold of WALL-CLOCK time from
    the decision) or "bars" (max_hold converted to that many M1 bars, i.e. trading
    time, for the real trade and its controls alike). Check `exposure_bars` in the
    result: if real and control mean tradable bars differ by more than ~10%
    (events clustered before the 17:00 NY halt or the weekend), rerun with "bars".

    Control: for every real trade `reps` random entries within +/-`window_days`,
    same direction, same stop distance, same target distance, same hold, same cost.
    ctrl_grid: "auto" (M1 minutes on the event's minute-of-hour grid), "m1"
    (any minute), or a timeframe like "1h" (draw bar closes of that series).
    ctrl_tod_tol_min: also match NY time-of-day within +/- this many minutes.
    cluster: optional column name or per-row array of cluster ids (e.g. a setup id
    whose trades fire on consecutive bars); bootstrapped as whole clusters.

    The verdict statistic is diff = mean(net R) - mean(control net R). Its CI is
    the WIDEST of the phase-3 CI (i.i.d. / event-block), a trading-day block
    bootstrap (mean block = `dependence.day_block_mean_days`) and the declared
    cluster bootstrap. Cost cancels in the differential but avg_R is reported net
    AND gross. If the real and control arms differ in their share of ambiguous
    same-bar exits by > rules.TIE_SHARE_TOL, the verdict must also hold with those
    bars scored 50/50, else UNTESTABLE (`ties`).
    """
    t0 = _time.time()
    mkt = get_market(m1)
    events_fp = frame_fingerprint(events)
    clu_vals, clu_desc = _cluster_arg(cluster, events, len(events))
    ev = _prepare(events if clu_vals is None else events.assign(_cluster=clu_vals),
                  max_hold)
    bk = _build_book(ev, mkt, entry_mode, reps, window_days, ctrl_grid, "auto"
                     if ctrl_grid == "auto" else 1, ctrl_tod_tol_min, seed, cost, m1,
                     hold_basis)
    tr = bk["trades"]
    n = len(tr)
    t = pd.DatetimeIndex(tr["decision_time"])
    real_r = tr["net_R"].to_numpy()
    cm = tr["ctrl_mean_R"].to_numpy()
    good = np.isfinite(cm)
    ctrl_r = bk["ctrl_r"]
    thr = resolve_threshold("trade", mde_threshold)
    settings = _settings(max_hold=max_hold if max_hold is not None else "per-row column",
                         cost=cost, reps=reps, window_days=window_days,
                         ctrl_grid=ctrl_grid, ctrl_tod_tol_min=ctrl_tod_tol_min,
                         entry_mode=entry_mode, hold_basis=hold_basis,
                         mde_threshold=mde_threshold, cluster=clu_desc,
                         n_boot=n_boot, seed=seed, tie="stop", resolution="M1")
    out = {"test_type": "trade", "claim": claim, "n_events_in": bk["n_in"], "dropped": bk["drop"],
           "n": n, "events_fp": events_fp, "settings": settings,
           "rules_version": rules.RULES_VERSION}
    if n < 2 or good.sum() < 2:
        v, det = verdict(diff=np.nan, ci_lo=np.nan, ci_hi=np.nan, n=n, halves=None,
                         mde=np.nan, mde_threshold=thr, claim=claim)
        out.update(verdict=v, verdict_detail=det, runtime_sec=round(_time.time() - t0, 2))
        _ledger(out, (events_fp,))
        return out

    day_codes = _day_codes(t[good])
    clu_codes = None
    if clu_vals is not None:
        cv = ev.set_index("ev_id").loc[tr["ev_id"], "_cluster"].to_numpy()
        clu_codes = _codes(cv[good])
    dep = _dep_days(utc_ns(t), tr["direction"].to_numpy(), bk["hold_ns"])
    n_days = int(day_codes.max()) + 1
    n_clu = int(clu_codes.max()) + 1 if clu_codes is not None else None
    n_eff = min(n_days, n_clu) if n_clu is not None else n_days

    d, lo, hi, how, comps, halves, blk = _paired_core(
        t, real_r, ctrl_r, cm, good, day_codes, clu_codes, dep, n_boot, seed, m1, split,
        blocks)
    real_w = (real_r > 0).astype(float)
    diff_win = float(real_w.mean() - (ctrl_r > 0).mean())

    st = _book_stats(real_r, bk["reason"])
    cst = _book_stats(ctrl_r, bk["ctrl_reason"])
    mde = mde_from_ci(lo, hi)
    flags = sanity_flags({"win": st["win_rate"] or np.nan, "exp_r": st["avg_R"] or np.nan,
                          "pf": st["pf"] if st["pf"] is not None else np.nan}, diff_win)
    vkw = dict(n=n, mde_threshold=thr, claim=claim, sanity_flags=flags, n_eff=n_eff,
               ctrl_overlap=bk["ctrl_overlap"])
    v, det = verdict(diff=d, ci_lo=lo, ci_hi=hi, halves=halves, mde=mde, **vkw)
    ties = dict(bk["ties"])
    v5050 = None
    if ties["real_ambiguous"] is not None and ties["control_ambiguous"] is not None and \
            abs(ties["real_ambiguous"] - ties["control_ambiguous"]) > rules.TIE_SHARE_TOL:
        r5 = tr["net_R_5050"].to_numpy()
        c5 = tr["ctrl_mean_R_5050"].to_numpy()
        d5, lo5, hi5, how5, _, h5, _ = _paired_core(
            t, r5, bk["ctrl_r_5050"], c5, good, day_codes, clu_codes, dep, n_boot, seed,
            m1, split, False)
        v5050, det5 = verdict(diff=d5, ci_lo=lo5, ci_hi=hi5, halves=h5,
                              mde=mde_from_ci(lo5, hi5), **vkw)
        ties.update(diff_5050=_f(d5), ci_5050=[_f(lo5), _f(hi5)], verdict_5050=v5050)
    ties["verdict_stop_first"] = v
    v, det = rules.tie_robust(v, det, v5050, ties["real_ambiguous"],
                              ties["control_ambiguous"])
    gross = tr["gross_R"].to_numpy()
    out.update({
        "span": {"start": str(t.min()), "end": str(t.max()),
                 "years": round((t.max() - t.min()).days / 365.25, 3)},
        "avg_R": st["avg_R"], "avg_R_gross": _f(gross.mean()), "win_rate": st["win_rate"],
        "pf": st["pf"], "sd_R": st["sd_R"], "exit_mix": st["exit_mix"],
        "trades_per_year": _f(n / max(1e-9, (t.max() - t.min()).days / 365.25)),
        "control": {**cst, "avg_R_gross": _f(np.mean(bk["ctrl_gross"])),
                    "reps": reps, "fill_rate": _f(bk["ctrl_fill"])},
        "diff": _f(d), "ci_lo": _f(lo), "ci_hi": _f(hi), "ci_method": how,
        "ci_components": _comps_json(comps),
        "p": _f(p_from_ci(d, lo, hi)), "diff_win": _f(diff_win),
        "halves": halves, "blocks": blk,
        "dependence": {"day_block_mean_days": dep, "n_days": n_days, "n_clusters": n_clu,
                       "n_eff": n_eff},
        "ties": ties, "ctrl_overlap": bk["ctrl_overlap"],
        "mde": _f(mde), "mde_threshold": thr, "power_floor_n": power_floor_n(n, mde, thr),
        "verdict": v, "verdict_detail": det, "sanity_flags": flags,
        "lookahead": {**bk["lookahead"], "entry_delay_min": bk["entry_delay_min"]},
        "exposure_bars": bk["exposure_bars"],
        "runtime_sec": round(_time.time() - t0, 2),
    })
    _ledger(out, (events_fp,))
    if keep_trades:
        out["_trades"] = tr
    return out


# ══ gate_test ═════════════════════════════════════════════════════════════════
def gate_test(baseline_events: pd.DataFrame, mask, *, mask_available_at,
              max_hold=None, claim: str = "+", cost=PRIMARY_COST, reps: int = CTRL_REPS,
              window_days: float = CTRL_WINDOW_DAYS, ctrl_grid="auto",
              ctrl_tod_tol_min: int | None = None, mde_threshold: float | None = None,
              entry_mode: str = "next_open", hold_basis: str = "clock",
              cluster=None, n_boot: int = N_BOOT, seed: int = SEED,
              split=SPLIT_DATE, blocks: bool = True, keep_trades: bool = False,
              m1: pd.DataFrame | None = None) -> dict:
    """Does a filter/condition improve a baseline trade book?

    `mask` marks the gated trades: preferably the NAME of a bool column of
    `baseline_events` (so the detector emits it and `probe_lookahead` checks it —
    write_result requires that unless the gate is declared a pure clock rule), or a
    bool array, one per row, no NaN. `mask_available_at` (UTC, one per row, or a
    column name) is when the gate's verdict was knowable — it must be <=
    decision_time on EVERY row, pass or fail ("never evaluated" and "passed" must
    not look alike). For a pure clock gate pass the decision_time itself. The
    stamp is only a declaration; the probe is the behavioural check.

    Statistic: control-adjusted R, adj_i = R_i - mean(control_i). diff =
    mean(adj | gated) - mean(adj | complement). Adjusting by each trade's own
    matched control removes geometry the gate may select for (bigger targets,
    tighter stops, calmer regimes). claim '+' = gated is better. CI and tie rules
    as in trade_test (the tie gap is the gated arm's excess over the complement's).
    """
    t0 = _time.time()
    mask_col = mask if isinstance(mask, str) else None
    if mask_col is not None:
        if mask_col not in baseline_events.columns:
            raise ValueError(f"mask column {mask_col!r} not in baseline_events")
        m = baseline_events[mask_col].to_numpy()
    else:
        m = np.asarray(mask)
    if m.dtype == object or (m.dtype.kind == "f" and np.isnan(m).any()):
        raise ValueError("mask contains NaN/None — decide unevaluated rows explicitly")
    m = m.astype(bool)
    if len(m) != len(baseline_events):
        raise ValueError("mask length != number of baseline events")
    if isinstance(mask_available_at, str):
        mask_available_at = baseline_events[mask_available_at]
    events_fp = frame_fingerprint(baseline_events)
    mask_fp = hashlib.sha1(np.packbits(m).tobytes() + str(len(m)).encode()).hexdigest()[:16]
    clu_vals, clu_desc = _cluster_arg(cluster, baseline_events, len(baseline_events))
    ev0 = baseline_events.copy()
    ev0["_gate"] = m
    ev0["_gate_av"] = _utc(mask_available_at)
    if clu_vals is not None:
        ev0["_cluster"] = clu_vals
    assert_no_lookahead(_utc(ev0["decision_time"]), ev0["_gate_av"], "gate mask")
    mkt = get_market(m1)
    ev = _prepare(ev0, max_hold)
    bk = _build_book(ev, mkt, entry_mode, reps, window_days, ctrl_grid,
                     "auto" if ctrl_grid == "auto" else 1, ctrl_tod_tol_min, seed, cost, m1,
                     hold_basis)
    tr = bk["trades"]
    evi = ev.set_index("ev_id")
    gate = evi.loc[tr["ev_id"], "_gate"].to_numpy(bool)
    tr["gate"] = gate
    t = pd.DatetimeIndex(tr["decision_time"])
    real_r = tr["net_R"].to_numpy()
    cm = tr["ctrl_mean_R"].to_numpy()
    good = np.isfinite(cm)
    adj = real_r - cm
    g, c = gate & good, (~gate) & good
    thr = resolve_threshold("gate", mde_threshold)
    ng, nc = int(g.sum()), int(c.sum())
    settings = _settings(max_hold=max_hold if max_hold is not None else "per-row column",
                         cost=cost, reps=reps, window_days=window_days,
                         ctrl_grid=ctrl_grid, ctrl_tod_tol_min=ctrl_tod_tol_min,
                         entry_mode=entry_mode, hold_basis=hold_basis,
                         mde_threshold=mde_threshold, cluster=clu_desc,
                         n_boot=n_boot, seed=seed, tie="stop", resolution="M1")
    out = {"test_type": "gate", "claim": claim, "n_events_in": bk["n_in"],
           "dropped": bk["drop"], "n": ng, "n_complement": nc,
           "gate_firing_rate": _f(gate.mean()) if len(gate) else None,
           "events_fp": events_fp, "mask_fp": mask_fp, "mask_col": mask_col,
           "settings": settings, "rules_version": rules.RULES_VERSION}
    if ng < 2 or nc < 2:
        v, det = verdict(diff=np.nan, ci_lo=np.nan, ci_hi=np.nan, n=ng, n_other=nc,
                         halves=None, mde=np.nan, mde_threshold=thr, claim=claim)
        out.update(verdict=v, verdict_detail=det, runtime_sec=round(_time.time() - t0, 2))
        _ledger(out, (events_fp, mask_fp))
        return out
    day_codes = _day_codes(t[good])
    days_all = np.asarray(trading_day(t))
    clu_codes = None
    cv = None
    if clu_vals is not None:
        cv = evi.loc[tr["ev_id"], "_cluster"].to_numpy()
        clu_codes = _codes(cv[good])
    dep = _dep_days(utc_ns(t), tr["direction"].to_numpy(), bk["hold_ns"])
    n_eff_g = len(np.unique(days_all[g]))
    n_eff_c = len(np.unique(days_all[c]))
    if cv is not None:
        n_eff_g = min(n_eff_g, len(pd.unique(cv[g])))
        n_eff_c = min(n_eff_c, len(pd.unique(cv[c])))
    n_eff = min(n_eff_g, n_eff_c)

    d, lo, hi, how, comps, halves, blk = _gate_core(
        t, adj, g, c, day_codes, clu_codes, dep, n_boot, seed, m1, split, blocks)
    tn = utc_ns(t)
    sp = np.datetime64(pd.Timestamp(split).tz_convert("UTC").tz_localize(None), "ns")
    halves["H1"]["n_gated"] = int((g & (tn < sp)).sum())
    halves["H2"]["n_gated"] = int((g & (tn >= sp)).sum())

    gst = _book_stats(real_r[gate], bk["reason"][gate])
    cst = _book_stats(real_r[~gate], bk["reason"][~gate])
    gd = _pair_ci(real_r[g], cm[g], real_r[g], cm[g], n_boot, seed + 5)
    cd = _pair_ci(real_r[c], cm[c], real_r[c], cm[c], n_boot, seed + 6)
    mde = mde_from_ci(lo, hi)
    diff_win = float((real_r[g] > 0).mean() - tr["ctrl_win"].to_numpy()[g].mean())
    flags = sanity_flags({"win": gst["win_rate"] or np.nan, "exp_r": gst["avg_R"] or np.nan,
                          "pf": gst["pf"] if gst["pf"] is not None else np.nan}, diff_win)
    vkw = dict(n=ng, n_other=nc, mde_threshold=thr, claim=claim, sanity_flags=flags,
               n_eff=n_eff, ctrl_overlap=bk["ctrl_overlap"])
    v, det = verdict(diff=d, ci_lo=lo, ci_hi=hi, halves=halves, mde=mde, **vkw)
    # ties: the gated arm's (real - control) ambiguous share vs the complement's
    tie_r = tr["tie"].to_numpy().astype(float)
    cnt = tr["ctrl_n"].to_numpy()
    ctrl_tie_mean = np.full(len(tr), np.nan)
    s_ = np.bincount(bk["ctrl_src"], weights=bk["ctrl_tie"].astype(float), minlength=len(tr))
    ctrl_tie_mean[cnt > 0] = s_[cnt > 0] / cnt[cnt > 0]
    ties = dict(bk["ties"])
    exc_g = float(np.nanmean(tie_r[g] - ctrl_tie_mean[g])) if ng else np.nan
    exc_c = float(np.nanmean(tie_r[c] - ctrl_tie_mean[c])) if nc else np.nan
    ties.update(gated_excess=_f(exc_g), complement_excess=_f(exc_c))
    v5050 = None
    if np.isfinite(exc_g) and np.isfinite(exc_c) and abs(exc_g - exc_c) > rules.TIE_SHARE_TOL:
        adj5 = tr["net_R_5050"].to_numpy() - tr["ctrl_mean_R_5050"].to_numpy()
        d5, lo5, hi5, _, _, h5, _ = _gate_core(t, adj5, g, c, day_codes, clu_codes, dep,
                                               n_boot, seed, m1, split, False)
        v5050, _ = verdict(diff=d5, ci_lo=lo5, ci_hi=hi5, halves=h5,
                           mde=mde_from_ci(lo5, hi5), **vkw)
        ties.update(diff_5050=_f(d5), ci_5050=[_f(lo5), _f(hi5)], verdict_5050=v5050)
    ties["verdict_stop_first"] = v
    v, det = rules.tie_robust(v, det, v5050, _f(exc_g), _f(exc_c))
    out.update({
        "span": {"start": str(t.min()), "end": str(t.max()),
                 "years": round((t.max() - t.min()).days / 365.25, 3)},
        "avg_R": gst["avg_R"], "avg_R_gross": _f(tr["gross_R"].to_numpy()[gate].mean()),
        "win_rate": gst["win_rate"], "pf": gst["pf"], "exit_mix": gst.get("exit_mix"),
        "gated_vs_own_control": {"diff": _f(gd[0]), "ci_lo": _f(gd[1]), "ci_hi": _f(gd[2]),
                                 "p": _f(p_from_ci(*gd[:3]))},
        "complement": {**cst, "vs_own_control": {"diff": _f(cd[0]), "ci_lo": _f(cd[1]),
                                                 "ci_hi": _f(cd[2]),
                                                 "p": _f(p_from_ci(*cd[:3]))}},
        "control": {"avg_R_gated": _f(np.nanmean(cm[g])), "avg_R_complement": _f(np.nanmean(cm[c])),
                    "reps": reps, "fill_rate": _f(bk["ctrl_fill"])},
        "diff": _f(d), "ci_lo": _f(lo), "ci_hi": _f(hi), "ci_method": how,
        "ci_components": _comps_json(comps),
        "p": _f(p_from_ci(d, lo, hi)), "diff_meaning": "mean(R-ctrl | gated) - mean(R-ctrl | complement)",
        "halves": halves, "blocks": blk,
        "dependence": {"day_block_mean_days": dep, "n_eff_gated": n_eff_g,
                       "n_eff_complement": n_eff_c, "n_eff": n_eff},
        "ties": ties, "ctrl_overlap": bk["ctrl_overlap"],
        "mde": _f(mde), "mde_threshold": thr,
        "power_floor_n": power_floor_n(min(ng, nc), mde, thr),
        "verdict": v, "verdict_detail": det, "sanity_flags": flags,
        "lookahead": {**bk["lookahead"], "gate_mask_checked": True,
                      "entry_delay_min": bk["entry_delay_min"]},
        "exposure_bars": bk["exposure_bars"],
        "runtime_sec": round(_time.time() - t0, 2),
    })
    _ledger(out, (events_fp, mask_fp))
    if keep_trades:
        out["_trades"] = tr
    return out


# ══ rate_test ═════════════════════════════════════════════════════════════════
def rate_test(observed, times, *, available_at, null=None, null_fn=None, null_p=None,
              reps: int = CTRL_REPS, claim: str = "+", mde_threshold: float | None = None,
              predictors: pd.DataFrame | None = None, cluster=None, outcome_horizon=None,
              n_boot: int = N_BOOT, seed: int = SEED, split=SPLIT_DATE,
              blocks: bool = True, m1: pd.DataFrame | None = None) -> dict:
    """Predictive-but-not-a-trade concepts: observed hit rate vs a MATCHED null.

    observed      per-event outcome, bool or 0/1 (or a fraction); NaN rows dropped
    times         per-event prediction time (UTC) — orders the block bootstrap and
                  assigns halves
    available_at  when the PREDICTOR (the level / window / condition) was known;
                  must be <= times (the outcome itself is of course later)
    predictors    the detector's frame (decision_time == times, row for row, plus
                  the level/window columns) — the frame `probe_lookahead` checked;
                  its fingerprint is what write_result matches against the probe
    Exactly one null:
      null_fn(rng, k) -> array (n,)   recomputes the outcome under the null for rep k
                                      (e.g. same level geometry at `sample_times`
                                      random moments, or shuffled levels) — called
                                      `reps` times with a seeded Generator
      null            array (n,) or (n, reps) of matched null outcomes
      null_p          array (n,) of analytic null probabilities (e.g. the window's
                      share of the day's traded minutes)
    Dependence: rows that SHARE an outcome (a per-day fact asked at every bar) are
    not independent. The CI is the widest of i.i.d., event-block, a trading-day
    block bootstrap with mean block = ceil(outcome_horizon / 1 day) (>= 1; pass
    the horizon when an outcome spans days, e.g. "5D" for a weekly level) and,
    when given, a bootstrap over `cluster` ids (e.g. one id per level).
    Statistic: diff = observed rate - null rate, paired per event; lift = ratio.
    """
    t0 = _time.time()
    obs = np.asarray(observed, dtype=float)
    tt = _utc(times)
    if len(obs) != len(tt):
        raise ValueError("observed and times lengths differ")
    look = assert_no_lookahead(tt, _utc(available_at), "rate predictor")
    if predictors is not None:
        if len(predictors) != len(tt) or "decision_time" not in predictors.columns or \
                not (utc_ns(predictors["decision_time"]) == utc_ns(tt)).all():
            raise ValueError("predictors must be the probed detector frame with "
                             "decision_time == times, row for row")
        events_fp = frame_fingerprint(predictors)
    else:
        events_fp = frame_fingerprint(pd.DataFrame({"decision_time": tt,
                                                    "available_at": _utc(available_at)}))
    clu_vals, clu_desc = _cluster_arg(cluster, predictors, len(obs))
    k_given = sum(x is not None for x in (null, null_fn, null_p))
    if k_given != 1:
        raise ValueError("give exactly one of null / null_fn / null_p")
    if null_fn is not None:
        rng = np.random.default_rng(seed)
        mat = np.column_stack([np.asarray(null_fn(rng, k), float) for k in range(reps)])
        null_kind = f"null_fn x{reps}"
    elif null is not None:
        mat = np.asarray(null, float)
        mat = mat[:, None] if mat.ndim == 1 else mat
        null_kind = f"null array x{mat.shape[1]}"
    else:
        mat = np.asarray(null_p, float)[:, None]
        null_kind = "analytic null_p"
    if mat.shape[0] != len(obs):
        raise ValueError("null rows != observed rows")
    hz = pd.Timedelta(outcome_horizon) if outcome_horizon is not None else pd.Timedelta("1D")
    dep = int(max(1, math.ceil(hz / pd.Timedelta("1D"))))
    order = np.argsort(utc_ns(tt), kind="stable")
    obs, mat, tt = obs[order], mat[order], tt[order]
    if clu_vals is not None:
        clu_vals = np.asarray(clu_vals)[order]
    keep = np.isfinite(obs) & np.isfinite(mat).any(axis=1)
    dropped = int((~keep).sum())
    obs, mat, tt = obs[keep], mat[keep], tt[keep]
    if clu_vals is not None:
        clu_vals = clu_vals[keep]
    n = len(obs)
    cnt = np.isfinite(mat).sum(axis=1)
    nm = np.where(cnt > 0, np.nansum(mat, axis=1) / np.maximum(cnt, 1), np.nan)
    pooled = mat[np.isfinite(mat)]
    null_rate = float(np.mean(nm)) if n else np.nan
    thr = resolve_threshold("rate", mde_threshold, null_rate)
    settings = _settings(reps=reps, n_boot=n_boot, seed=seed, mde_threshold=mde_threshold,
                         cluster=clu_desc, outcome_horizon=str(hz), null_kind=null_kind)
    out = {"test_type": "rate", "claim": claim, "n": n, "dropped": {"nan_rows": dropped},
           "null_kind": null_kind, "events_fp": events_fp,
           "predictors_probed": predictors is not None, "settings": settings,
           "rules_version": rules.RULES_VERSION}
    if n < 2:
        v, det = verdict(diff=np.nan, ci_lo=np.nan, ci_hi=np.nan, n=n, halves=None,
                         mde=np.nan, mde_threshold=thr, claim=claim)
        out.update(verdict=v, verdict_detail=det, runtime_sec=round(_time.time() - t0, 2))
        _ledger(out, (events_fp,))
        return out
    d, lo_p, hi_p, how_p = _pair_ci(obs, pooled, obs, nm, n_boot, seed)
    comps = {f"phase3_{how_p}": (lo_p, hi_p)}
    day_codes = _day_codes(tt)
    stat = (lambda a, b, c: (a - b) / c)
    ones = np.ones(n)
    comps["day_block"] = _bucket_ci(day_codes, [obs, nm, ones], stat, n_boot, seed + 11, 1)
    if dep > 1:
        comps[f"day_block_{dep}d"] = _bucket_ci(day_codes, [obs, nm, ones], stat, n_boot,
                                                seed + 12, dep)
    n_days = int(day_codes.max()) + 1
    n_clu = None
    if clu_vals is not None:
        cc = _codes(clu_vals)
        n_clu = int(cc.max()) + 1
        comps["cluster"] = _bucket_ci(cc, [obs, nm, ones], stat, n_boot, seed + 13, 1)
    n_eff = min(n_days, n_clu) if n_clu is not None else n_days
    lo, hi, how = _widest(d, comps)

    def fn(sel):
        return _pair_ci(obs[sel], nm[sel], obs[sel], nm[sel], max(500, n_boot // 2), seed + 17)
    halves, blk = _halves_blocks(tt, fn, m1, split, blocks)
    mde = mde_from_ci(lo, hi)
    v, det = verdict(diff=d, ci_lo=lo, ci_hi=hi, n=n, halves=halves, mde=mde,
                     mde_threshold=thr, claim=claim, n_eff=n_eff)
    obs_rate = float(obs.mean())
    out.update({
        "span": {"start": str(tt.min()), "end": str(tt.max()),
                 "years": round((tt.max() - tt.min()).days / 365.25, 3)},
        "observed_rate": _f(obs_rate), "null_rate": _f(null_rate),
        "lift": _f(obs_rate / null_rate) if null_rate else None,
        "control": {"rate": _f(null_rate), "reps": int(mat.shape[1]), "kind": null_kind},
        "diff": _f(d), "ci_lo": _f(lo), "ci_hi": _f(hi), "ci_method": how,
        "ci_components": _comps_json(comps),
        "p": _f(p_from_ci(d, lo, hi)),
        "halves": halves, "blocks": blk,
        "dependence": {"day_block_mean_days": dep, "n_days": n_days, "n_clusters": n_clu,
                       "n_eff": n_eff},
        "mde": _f(mde), "mde_threshold": thr, "power_floor_n": power_floor_n(n, mde, thr),
        "verdict": v, "verdict_detail": det, "sanity_flags": [],
        "lookahead": look,
        "runtime_sec": round(_time.time() - t0, 2),
    })
    _ledger(out, (events_fp,))
    return out
