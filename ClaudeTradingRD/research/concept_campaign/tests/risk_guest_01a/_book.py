"""Shared baseline book for batch risk_guest_01a (risk concepts, guest voice).

The risk concepts in this batch are rules applied to a stream of trades (daily caps,
stop-after-N-losses, streak-based sizing, management variants). They need a baseline
trade book. Declared before any run, for every concept in this batch:

  BASELINE = phase-3 rung-0 bare CISD on 15m bars (the harness's own worked example:
  level_rule series_open, swings 2/2, max_wait 3, min_series 1), decided at the
  confirming bar's close, entered at the next M1 open, stop at the protected swing,
  2R target, 150-minute wall-clock hold (10 entry-TF bars, phase-3 section 1.13),
  taken ONE POSITION AT A TIME: a signal is skipped while an earlier taken trade is
  still open (a trader who counts trades and losses takes them sequentially).

The sequential chain needs each taken trade's exit. It is resolved here on M1 with the
harness's own resolver (`resolve_trades`, stop-first ties) from the M1 frame passed in,
so it is causal: a trade's exit is "known" at the close of its exit bar, and a trade
whose hold window runs past the end of the data it was given and has not hit its stop
or target is UNRESOLVED (still open) - never guessed. Every state column below reads
only trades whose exit was known at or before the row's decision_time.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from concept_lab.data import utc_ns   # noqa: E402
from concept_lab.engine import Market, resolve_trades   # noqa: E402
from detectors.cisd import cisd_events   # noqa: E402

TF = "15min"
RR = 2.0
MAX_HOLD = pd.Timedelta("150min")
ONE_MIN = np.int64(60_000_000_000)

BASE_PARAMS = {"baseline_tf": TF, "level_rule": "series_open", "swing": "2/2",
               "max_wait": 3, "min_series": 1, "rr": RR, "max_hold": "150min",
               "sequencing": "one position at a time"}
BASE_SOURCES = {
    "baseline_tf": "phase3: primary stack entry TF (15m), harness example_gate baseline",
    "level_rule": "phase3: meta/conjunction_preregistration.md locked CISD config",
    "swing": "phase3: meta/conjunction_preregistration.md locked CISD config",
    "max_wait": "phase3: meta/conjunction_preregistration.md locked CISD config",
    "min_series": "phase3: meta/conjunction_preregistration.md locked CISD config",
    "rr": "phase3: 2R target (rung 0); also the guests' stated ~2:1 payoff",
    "max_hold": "phase3: 10 entry-TF bars (section 1.13)",
    "sequencing": "declared-before-run: a trader counting trades/losses holds one "
                  "position at a time; signals while a position is open are skipped",
}


def raw_cisd(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=["decision_time", "available_at", "direction",
                                     "stop_px"])
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(ev["direction"] == "bullish", 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(float)})
    # deterministic order for the 4 bars (of 32,827 events) where a bullish and a
    # bearish CISD confirm on the same bar: long first. cisd_events' own order for such
    # a pair depends on the slice it was given, which the probe caught.
    return out.sort_values(["decision_time", "direction", "stop_px"],
                           ascending=[True, False, True],
                           kind="stable").reset_index(drop=True)


def resolve(m1: pd.DataFrame, dec: pd.DatetimeIndex, sgn: np.ndarray, stop: np.ndarray,
            tgt_rr: float | np.ndarray = RR, hold=MAX_HOLD, mkt: Market | None = None):
    """Resolve trades like the harness does (next-open entry, clock hold, stop-first).

    Returns dict: valid, entry, risk, R (gross), exit_known_ns (inf when unresolved).
    """
    mkt = mkt if mkt is not None else Market(m1)
    N = len(mkt.tn)
    dn = utc_ns(dec)
    i0 = np.searchsorted(mkt.tn, dn, side="left")
    ok = i0 < N
    i0c = np.clip(i0, 0, N - 1)
    entry = mkt.o[i0c]
    risk = sgn * (entry - stop)
    ok &= np.isfinite(risk) & (risk > 0)
    if isinstance(hold, pd.Timedelta):
        hold_ns = np.int64(hold.value)
    else:
        hold_ns = np.asarray(pd.to_timedelta(hold).asi8, dtype=np.int64)
    end_ns = dn + hold_ns
    i1 = np.searchsorted(mkt.tn, end_ns, side="left")
    ok &= i1 > i0
    tgt = entry + sgn * np.asarray(tgt_rr, float) * risk
    n = len(dn)
    R = np.full(n, np.nan)
    known = np.full(n, np.inf)
    reason = np.full(n, -1, np.int8)
    if ok.any():
        k = np.flatnonzero(ok)
        r = resolve_trades(mkt, sgn[k] > 0, stop[k], tgt[k], i0[k], i1[k])
        R[k] = sgn[k] * (r["exit_px"] - entry[k]) / risk[k]
        reason[k] = r["reason"]
        kn = mkt.tn[r["exit_pos"]].astype(np.float64) + float(ONE_MIN)
        # a time exit is only known once the hold's wall-clock end has passed (a hold
        # ending inside the 17:00 NY halt must not free the slot at the last pre-halt
        # bar: that would read "no bars until the hold ends" from the data)
        tx = r["reason"] == 2
        kn[tx] = np.maximum(kn[tx], end_ns[k][tx].astype(np.float64))
        # a time exit whose hold window ran past the data we were given is unresolved
        last_close = float(mkt.tn[-1] + ONE_MIN)
        unresolved = (r["reason"] == 2) & (end_ns[k].astype(np.float64) > last_close)
        kn[unresolved] = np.inf
        R[k[unresolved]] = np.nan
        known[k] = kn
    # a trade the harness will drop (entry gapped past the stop, or no bar in the hold)
    # opens no position: its slot frees at the close of the would-be entry bar. A row
    # with no bar after its decision (end of the given data) stays unresolved (inf).
    dead = (~ok) & (i0 < N)
    known[dead] = mkt.tn[i0c[dead]].astype(np.float64) + float(ONE_MIN)
    return {"valid": ok, "entry": entry, "risk": risk, "R": R, "known": known,
            "reason": reason, "i0": i0, "mkt": mkt}


def week_key(td: pd.DatetimeIndex) -> np.ndarray:
    sd = td + pd.Timedelta(days=1)                    # Sunday-opened session -> Monday
    return (sd - pd.to_timedelta(sd.dayofweek, unit="D")).to_numpy()


def chain(m1: pd.DataFrame) -> pd.DataFrame:
    """The sequential baseline book with per-row state from earlier taken trades.

    Columns: decision_time, available_at, direction, stop_px, rr, plus
      _R (this trade's gross R on M1 - NOT used as an input to any gate; kept only for
          the stateful rules that need earlier outcomes), _known_ns,
      tday, wkey, day_rank (1 = first taken trade of the trading day),
      day_losses_before, day_wins_before, day_R_before, week_R_before, week_n_before,
      consec_losses_before, consec_wins_before, prev_outcome (+1 win, -1 loss, 0 none/flat)
    """
    ev = raw_cisd(m1)
    dec = pd.DatetimeIndex(ev["decision_time"])
    sgn = ev["direction"].to_numpy(np.int64)
    stop = ev["stop_px"].to_numpy(float)
    res = resolve(m1, dec, sgn, stop)
    # NO filtering on the trade's own validity: that reads the next M1 open (the
    # future). The harness drops invalid rows itself; here they only free the slot.
    R = res["R"]
    known = res["known"]
    dn = utc_ns(pd.DatetimeIndex(ev["decision_time"])).astype(np.float64)
    taken = np.zeros(len(ev), bool)
    free_at = -np.inf
    for k in range(len(ev)):
        if dn[k] >= free_at:
            taken[k] = True
            free_at = known[k]
    ev = ev[taken].reset_index(drop=True)
    R = R[taken]
    known = known[taken]
    ev["rr"] = RR
    ev["_R"] = R
    ev["_known_ns"] = known
    td = cl.trading_day(pd.DatetimeIndex(ev["decision_time"]))
    ev["tday"] = td.to_numpy()
    ev["wkey"] = week_key(td)
    n = len(ev)
    day_rank = np.zeros(n, np.int64)
    dl = np.zeros(n, np.int64); dw = np.zeros(n, np.int64)
    dR = np.zeros(n); wR = np.zeros(n); wn = np.zeros(n, np.int64)
    cl_ = np.zeros(n, np.int64); cw = np.zeros(n, np.int64); prev = np.zeros(n, np.int64)
    tdv = ev["tday"].to_numpy(); wkv = ev["wkey"].to_numpy()
    cur_d = None; cur_w = None
    r_d = 0; l_d = 0; w_d = 0; R_d = 0.0; R_w = 0.0; n_w = 0
    s_l = 0; s_w = 0; pv = 0
    for k in range(n):
        # every earlier taken trade is resolved by now (one position at a time)
        if tdv[k] != cur_d:
            cur_d = tdv[k]; r_d = 0; l_d = 0; w_d = 0; R_d = 0.0
        if wkv[k] != cur_w:
            cur_w = wkv[k]; R_w = 0.0; n_w = 0
        r_d += 1
        day_rank[k] = r_d; dl[k] = l_d; dw[k] = w_d; dR[k] = R_d; wR[k] = R_w
        wn[k] = n_w; cl_[k] = s_l; cw[k] = s_w; prev[k] = pv
        rk = R[k]
        if not np.isfinite(rk):          # unresolved, or a row the harness drops
            continue
        R_d += rk; R_w += rk; n_w += 1
        if rk > 0:
            w_d += 1; s_w += 1; s_l = 0; pv = 1
        elif rk < 0:
            l_d += 1; s_l += 1; s_w = 0; pv = -1
        else:
            pv = 0
    ev["day_rank"] = day_rank
    ev["day_losses_before"] = dl
    ev["day_wins_before"] = dw
    ev["day_R_before"] = dR
    ev["week_R_before"] = wR
    ev["week_n_before"] = wn
    ev["consec_losses_before"] = cl_
    ev["consec_wins_before"] = cw
    ev["prev_outcome"] = prev
    return ev


BASE_RULES = [
    "baseline: 15m bare CISD (series_open, 2/2 swings, max_wait 3), decided at the "
    "confirming 15m bar's close, next-M1-open entry, stop at the protected swing, 2R, "
    "150-min clock hold",
    "one position at a time: a signal is skipped while the previous taken trade is open "
    "(exit known at the close of its M1 exit bar, resolved with the harness resolver)",
]


def public(ev: pd.DataFrame, extra: list[str]) -> pd.DataFrame:
    """The scored frame: harness columns + the gate/state columns the rule reads."""
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"] + extra
    return ev[cols].reset_index(drop=True)


def _self_version() -> str:
    import hashlib
    return hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:10]


from pathlib import Path  # noqa: E402
VERSION = _self_version()   # pass to cache_frame(version=) so edits here rebuild caches
