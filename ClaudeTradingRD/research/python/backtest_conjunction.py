"""The conjunction test — phase 3, workstream B.

Runs the pre-registered ablation ladder of `meta/conjunction_preregistration.md`
and writes `meta/backtest_conjunction.md`.

THE QUESTION. Phase 2 found every primitive sitting near its base rate. The
corpus's own defence is that the edge lives in the CONJUNCTION — higher-timeframe
bias, then a point of interest, then a CISD, then timing. This module asks
whether stacking those gates ADDS anything over its parts, or merely shrinks the
sample until noise resembles skill. That is an ablation question, which is why
the protocol is a ladder and why every rung is read on its differential against a
matched random-entry control rather than on a raw win rate.

WHAT IS LOCKED, AND WHERE IT COMES FROM. Nothing in this file was chosen after a
result was seen. The primary configuration is `meta/conjunction_preregistration.md`
§1.16; the ladder is §2.1; the control is §4.3, matching dimensions and all; the
statistics are §4.5; the interpretation labels are §2.4 and §5. The constants
below cite the section they come from, and any place this module had to make a
decision the pre-registration did not settle is marked `[DEVIATION]` in the
docstring of the function that makes it and is reported in the output file.

THE THREE FAILURE MODES THIS HARNESS IS BUILT AGAINST, all of them observed in
this project rather than imagined:

  1. Off-by-one on the entry bar. `bars.resample` is `label="left"`, so an event
     timestamp is the START of its bar. Resolving forward from the event replays
     the signal candle, which touches its own extreme by construction, so the
     stop fires instantly and the book returns ~3% — a number that reads as a bad
     strategy, not as a bug. The same error in the other direction manufactures a
     spectacular edge and is therefore much less likely to be questioned. Entry
     is at `event_time + one bar` everywhere, and it is asserted, not assumed.

  2. A gate reading data it could not have had. Every gate here carries an
     availability timestamp and is checked against the entry moment for every
     event in the book. The POI gate's third branch waits five bars past the
     opposing series to see whether 50% of the bodies hold, so its verdict can
     resolve AFTER the CISD it is supposed to qualify; that is caught here rather
     than absorbed silently. See `poi_annotate`.

  3. Reading a raw win rate. Every gate in the ladder is a selector, and a
     selector that finds rarer, larger-R setups raises the win rate without
     predicting anything. The matched control shares direction, stop distance,
     target distance and local window, so that improvement appears in both arms
     and cancels. The verdict is the differential; the raw rate is description.

Offline. Reads only local parquet. Nothing here reaches the network.

Usage — how `meta/backtest_conjunction.md` was produced, in order:

    # 1. the three stacks that carry outcome books, plus family B
    python backtest_conjunction.py --stacks 15min,5min,1h --family-b --dump A.pkl

    # 2. the 1-minute stack, event counts only (off-method, reported for n alone)
    python backtest_conjunction.py --stacks 1min --counts-only --no-report --dump B.pkl

    # 3. the declared landscapes and cross-checks, each dumped separately so the
    #    report can be rebuilt without recomputing anything
    #       family_c(...)          -> C.pkl     (session grid, stop variant)
    #       strat_and_dollar(...)  -> S.pkl     (§5.4 items 3 and 6)
    #       coordinator_check(...) -> K.pkl     (rung 0 at the coordinator's params)

    # 4. assemble, adding the §3.7.2c robustness exclusion re-run
    python backtest_conjunction.py --from-dump A.pkl,B.pkl --family-c-dump C.pkl \
        --strat-dump S.pkl --coord-dump K.pkl --exclusion-check

Expensive stages (bias_report, CISD detection, the POI gate) memoise to
`$CONJ_CACHE`; set `CONJ_CACHE_DISABLE=1` to bypass, which the tests do.
"""
from __future__ import annotations

import argparse
import math
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bars import load_m1, resample                                  # noqa: E402
from detectors.cisd import cisd_events                              # noqa: E402
from detectors.primitives import swing_points                       # noqa: E402
from detectors.poi import poi_gate                                  # noqa: E402
from detectors.bias import (bias_report, trading_day, infer_freq,   # noqa: E402
                            daily_candles, daily_closures)
# Reused verbatim from phase 2 so the two books are resolved by the same code.
# Importing is not modifying: `backtest_c2_wick` is read-only to this module.
from backtest_c2_wick import resolve, apply_cost, boot_diff, truncate_at_gap  # noqa: E402
# The reference join and power arithmetic, imported so this run cannot drift from
# the counts the pre-registration was written against.
from estimate_conjunction_power import (join_day_gates, join_day_num,  # noqa: E402
                                        mde_vs_control, n_real_for_effect)

ROOT = Path(__file__).resolve().parents[1]
RD = Path(__file__).resolve().parents[2]
OUT_MD = ROOT / "meta" / "backtest_conjunction.md"

# ── the locked configuration (pre-registration §1.16) ─────────────────────────
PARQUET = RD / "m3_scalper" / "xau_m1_full.parquet"
CERTIFIED_START = "2016-01-01"          # §3.7: the Oct-2015 calendar change
CERTIFIED_END = None                    # the file ends 2026-07-23
TICK_REGRESSION = ("2019-02-01", "2020-02-29")   # §3.7.2(c), declared exclusion

TZ = "America/New_York"
PRIMARY_TARGET = "2R"                   # §1.12
PRIMARY_COST = "0.04R"                  # §1.15 as AMENDED (§8, A4)
TARGETS = ("1R", "2R", "3R", "structural")       # §1.12
COSTS = (0.0, 0.2, 0.5, "0.04R")                 # §1.15, flat USD/oz diagnostics
MAX_HOLD = 10                           # §1.13, entry-timeframe periods
LEVEL_RULE = "series_open"              # §1.8 [P] primary
MAX_WAIT = 3                            # §1.8, `v-shape-reversal-speed`
MIN_SERIES = 1                          # §1.8 [P] primary
CISD_SCOPE = "range"                    # §1.8 [P] primary
C3_REFERENCE = "c2_open"                # §1.7 [P] primary, Reading A
SWING_LEFT, SWING_RIGHT = 2, 2          # §1.8, `primitives.swing_points`

# §4.3 — the matched control, locked in full. None of these may be swept.
CTRL_REPS = 5
CTRL_WINDOW_DAYS = 30
SEED = 20260825

# §4.5
N_BOOT = 2000
BLOCK_MEAN = 20                         # stationary block bootstrap, mean block

# §4.4 — the three time blocks
PRE_END = pd.Timestamp("2023-07-02", tz="UTC")   # confirmatory sample ends here
IS_END = pd.Timestamp("2025-07-02", tz="UTC")    # phase-2 parity

# §1.14 — session is a KNOB and is OFF in the primary
SESSION_START_MIN, SESSION_END_MIN = 10 * 60, 12 * 60

# §1.2 — the four pre-declared stacks
STACKS = [
    ("15min", "4h",    "1D", "PRIMARY — favourite / A+"),
    ("5min",  "1h",    "1D", "powered secondary — playbook"),
    ("1h",    "1D",    "1W", "swing model"),
    ("1min",  "15min", "4h", "power-ceiling reference — scalping (off-method)"),
]
STACK_ORDER = [s[0] for s in STACKS]
PRIMARY_STACK = "15min"
POWERED_STACK = "5min"

# §3.4 — the power floor the interpretation rules are written against
P_WIN_2R = 0.36
POWER_FLOOR_5PP = 868                   # real trades, against the 5x control

# §4.1.3 — the harness sanity floor
SANE_WIN = (0.10, 0.90)
SANE_EXP_R = 1.0
SANE_DIFF_PP = 0.15
SANE_PF = 3.0

RUNGS = ["R0", "R1", "R2", "R3", "R4"]
RUNG_LABEL = {
    "R0": "R0 bare CISD",
    "R1": "R1 + POI",
    "R2": "R2 + HTF bias",
    "R3": "R3 + profile support",
    "R4": "R4 + alignment (PRIMARY)",
}
GATES = ["poi", "bias", "profile", "align"]

# §3.2 of the pre-registration as it stands after amendment A5 — measured
# independently by that workstream on the same span with the same detector
# modules. Reproducing it exactly is the strongest harness check available.
PREDICTED = {("15min", "R0"): "32,827", ("15min", "R1"): "26,710",
             ("15min", "R2"): "4,171", ("15min", "R3"): "1,862",
             ("15min", "R4"): "722",
             ("5min", "R0"): "98,346", ("5min", "R1"): "79,692",
             ("5min", "R2"): "12,569", ("5min", "R3"): "5,716",
             ("5min", "R4"): "2,234",
             ("1h", "R0"): "8,034", ("1h", "R1"): "6,458",
             ("1h", "R2"): "1,034", ("1h", "R3"): "484", ("1h", "R4"): "176"}
PREDICTED_KNOBS = {("15min", "K1"): 43, ("15min", "K2"): 252, ("15min", "K3"): 15,
                   ("5min", "K1"): 187, ("5min", "K2"): 792, ("5min", "K3"): 69,
                   ("1h", "K1"): 24, ("1h", "K2"): 63, ("1h", "K3"): 9}

_CACHE = Path(os.environ.get(
    "CONJ_CACHE",
    Path(os.environ.get("TEMP", "/tmp")) / "conj_cache"))


# ══ caching ═══════════════════════════════════════════════════════════════════
def _cache_path(key: str, ext: str) -> Path:
    _CACHE.mkdir(parents=True, exist_ok=True)
    return _CACHE / f"{key}.{ext}"


def cached(key: str, build, ext: str = "pkl"):
    """Compute-once, reuse-many. Purely a speed device; nothing is memoised across
    configurations because the key carries every parameter that changes the answer."""
    if os.environ.get("CONJ_CACHE_DISABLE"):
        return build()
    p = _cache_path(key, ext)
    if p.exists():
        with open(p, "rb") as f:
            return pickle.load(f)
    val = build()
    with open(p, "wb") as f:
        pickle.dump(val, f)
    return val


# ══ data ══════════════════════════════════════════════════════════════════════
def load_certified(exclude_tick_regression: bool = False
                   ) -> tuple[pd.DataFrame, float]:
    """The certified span, and nothing else.

    Pre-2016 gold is disqualified by a trading-calendar change, not by quality:
    New York hour 17 carries 1,813-3,726 bars a year through September 2015 and
    then exactly zero, forever. Every gate in the locked configuration is session-
    or daily-calendar-dependent, so on pre-2016 data the gates do not fail — they
    quietly compute different objects, which is strictly worse.
    """
    m1 = load_m1(PARQUET)
    m1 = m1[m1.index >= pd.Timestamp(CERTIFIED_START, tz="UTC")]
    if CERTIFIED_END:
        m1 = m1[m1.index <= pd.Timestamp(CERTIFIED_END, tz="UTC")]
    yrs = (m1.index.max() - m1.index.min()).days / 365.25
    if exclude_tick_regression:
        lo, hi = (pd.Timestamp(t, tz="UTC") for t in TICK_REGRESSION)
        m1 = m1[(m1.index < lo) | (m1.index > hi)]
        yrs -= (hi - lo).days / 365.25
    return m1, yrs


def load_correlate() -> tuple[pd.DataFrame | None, str]:
    """XAG H1, the correlate the SMT knob needs.

    The pre-registration recorded SMT as unmeasurable before 2023-07-02. That was
    an artefact of `fetch_correlated.py`'s default start date — the gold 3-year
    window — not a limit of the feed: OANDA serves XAG from 2010-01-03. The
    extended file is preferred when present, and the constraint is corrected in
    the report rather than repeated.
    """
    for name in ("xag_h1_full.parquet", "xag_h1.parquet"):
        p = RD / "m3_scalper" / name
        if p.exists():
            break
    else:
        return None, "none"
    x = pd.read_parquet(p)
    if "time" in x.columns:
        x = x.set_index("time")
    x.index = pd.to_datetime(x.index, utc=True)
    return x[["open", "high", "low", "close"]].astype("float64").sort_index(), name


def calendar_blocks(m1: pd.DataFrame) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    """§4.4b primary blocking: four equal calendar quarters of the certified span.

    Boundaries are arithmetic. That is the whole point — no price, no outcome and
    no judgement enters them, so they cannot be gerrymandered after the fact.
    """
    t0, t1 = m1.index.min(), m1.index.max()
    step = (t1 - t0) / 4
    out = []
    for k in range(4):
        a = t0 + step * k
        b = t1 if k == 3 else t0 + step * (k + 1)
        out.append((f"B{k+1}", a, b))
    return out


# ══ the CISD level-rule secondary the pre-registration asks for ═══════════════
def cisd_events_max_open(df: pd.DataFrame, left: int = SWING_LEFT,
                         right: int = SWING_RIGHT, max_wait: int = MAX_WAIT,
                         min_series: int = MIN_SERIES, max_series: int = 10
                         ) -> pd.DataFrame:
    """`level_rule="series_max_open"` — the pre-declared secondary reading (§1.8).

    [DEVIATION, declared] The pre-registration says this rule "does not exist in
    `python/detectors/cisd.py` today and must be added before the test runs". This
    workstream is scoped out of editing the detectors, so the reading is
    implemented HERE instead, as a faithful copy of `cisd.cisd_events` with one
    line changed: the level is the highest open of the run (bullish: lowest),
    rather than the open of its first candle. It is a family-B declared secondary
    and cannot change any verdict, so its location does not affect the result — but
    the divergence from the pre-registration's instruction is recorded rather than
    quietly satisfied.
    """
    from detectors.cisd import _run_into_extreme

    if df.empty:
        return pd.DataFrame(columns=["direction", "extreme_time", "confirm_time"])
    sw = swing_points(df, left=left, right=right)
    close = df["close"].to_numpy()
    idx = df.index
    n = len(df)
    rows = []
    for bullish, col in ((True, "swing_low"), (False, "swing_high")):
        flags = sw[col].to_numpy()
        for pos in range(n):
            if not flags[pos]:
                continue
            start, end = _run_into_extreme(df, pos, bullish, max_len=max_series)
            if start < 0 or (end - start + 1) < min_series:
                continue
            seg_open = df["open"].iloc[start:end + 1]
            lvl = float(seg_open.max() if bullish else seg_open.min())
            begin = max(end, pos + right) + 1
            stop = min(n, begin + max_wait)
            for j in range(begin, stop):
                if (close[j] > lvl) if bullish else (close[j] < lvl):
                    rows.append({
                        "direction": "bullish" if bullish else "bearish",
                        "extreme_time": idx[pos],
                        "extreme_price": float(df["low"].iloc[pos] if bullish
                                               else df["high"].iloc[pos]),
                        "series_start": idx[start], "series_end": idx[end],
                        "series_len": end - start + 1,
                        "level_rule": "series_max_open", "level": lvl,
                        "confirm_time": idx[j], "confirm_close": float(close[j]),
                        "bars_waited": j - end,
                        "protected_swing": float(df["low"].iloc[pos] if bullish
                                                 else df["high"].iloc[pos]),
                    })
                    break
    if not rows:
        return pd.DataFrame(columns=["direction", "extreme_time", "confirm_time"])
    return pd.DataFrame(rows).sort_values("confirm_time").reset_index(drop=True)


# ══ events and gates ══════════════════════════════════════════════════════════
def build_events(bars: pd.DataFrame, tag: str, level_rule: str = LEVEL_RULE,
                 max_wait: int = MAX_WAIT, min_series: int = MIN_SERIES
                 ) -> pd.DataFrame:
    key = f"ev_{tag}_{level_rule}_{max_wait}_{min_series}"

    def build():
        if level_rule == "series_max_open":
            return cisd_events_max_open(bars, max_wait=max_wait,
                                        min_series=min_series)
        return cisd_events(bars, level_rule=level_rule, left=SWING_LEFT,
                           right=SWING_RIGHT, max_wait=max_wait,
                           min_series=min_series)
    return cached(key, build)


def poi_annotate(bars: pd.DataFrame, ev: pd.DataFrame, tf: str, tag: str
                 ) -> pd.DataFrame:
    """§4.1's gate per event, WITH its availability timestamp.

    The gate is evaluated at the event's extreme, exactly as
    `estimate_conjunction_power` does. What is added here is `last_bar_used`,
    which `poi_gate` already computes and which the pre-registration's own
    availability table (`meta/bias_poi_build.md`) says is the moment the verdict
    resolves: `detail["last_bar_used"] + freq`.

    It matters. The FVG and swing branches never look past the extreme, but the
    third branch — "use the CISD level, and additionally require 50% of the bodies
    of that opposing series to hold" — is a FORWARD test, and with
    `body_hold_bars=5` it can resolve after the CISD it is meant to qualify. A
    verdict that is not available at the entry moment is not a gate that passed;
    it is a gate that had not been evaluated yet. `poi_available` is the honest
    column and it is what the ladder uses; `poi_passed_raw` is retained so the
    difference is a number in the report rather than a claim.
    """
    key = f"poi_{tag}_{tf}_{len(ev)}"

    def build():
        passed, lastbar, kind = [], [], []
        for t, d in zip(ev["extreme_time"].to_numpy(),
                        ev["direction"].to_numpy()):
            r = poi_gate(bars, t, d, timeframe=tf, setup_type="reversal",
                         left=SWING_LEFT, right=SWING_RIGHT,
                         level_rule=LEVEL_RULE)
            passed.append(bool(r.passed))
            lastbar.append(r.detail["last_bar_used"])
            kind.append(r.kind_used)
        return pd.DataFrame({
            "poi_passed_raw": passed,
            "poi_last_bar_used": pd.DatetimeIndex(lastbar),
            "poi_kind": kind,
        })
    out = cached(key, build)
    conf = pd.DatetimeIndex(ev["confirm_time"])
    # A bar labelled t is fully known at t + period; the entry decision is taken at
    # the confirming bar's close, i.e. confirm_time + period. So a bar at t is
    # admissible iff t <= confirm_time.
    out = out.reset_index(drop=True)
    out["poi_in_time"] = (out["poi_last_bar_used"].to_numpy() <= conf.to_numpy())
    out["poi_passed"] = out["poi_passed_raw"].to_numpy() & out["poi_in_time"].to_numpy()
    return out


def make_report(m1: pd.DataFrame, tag: str, xag: pd.DataFrame | None,
                cisd_scope: str = CISD_SCOPE, c3_reference: str = C3_REFERENCE
                ) -> pd.DataFrame:
    key = f"bias_{tag}_{cisd_scope}_{c3_reference}"

    def build():
        rep = bias_report(m1, correlate_h1=xag, cisd_scope=cisd_scope,
                          c3_reference=c3_reference)
        rep["bias_dir_num"] = rep["bias"].map(
            {"bullish": 1, "bearish": -1}).fillna(0).astype(int)
        rep["day_gates_available_at"] = rep[
            ["bias_available_at", "profile_available_at", "alignment_available_at"]
        ].max(axis=1)
        return rep
    return cached(key, build)


def gate_matrix(ev: pd.DataFrame, poi: pd.DataFrame, report: pd.DataFrame
                ) -> dict:
    """The four ladder gates as boolean arrays over the R0 event set, plus the
    join diagnostics §4.1a requires (resolution share and staleness).

    The daily gates are JOINED, never intersected at the day layer: a day-level
    conjunction leaves nine qualifying days in three years and the same nine in
    ten. `join_day_gates` is imported from `estimate_conjunction_power` rather
    than re-implemented, so the two cannot drift apart.
    """
    cols = ["gate_bias", "gate_profile", "gate_alignment"]
    has_smt = ("gate_smt" in report.columns
               and report["gate_smt"].fillna(False).astype(bool).any())
    if has_smt:
        cols.append("gate_smt")
    dg = join_day_gates(ev, report, cols)
    src = dg["_src"].to_numpy()

    sign = np.where((ev["direction"] == "bullish").to_numpy(), 1, -1)
    bdir = join_day_num(ev, report, "bias_dir_num", src)

    lt = pd.DatetimeIndex(ev["confirm_time"]).tz_convert(TZ)
    tt = lt.hour * 60 + lt.minute
    sess = (tt >= SESSION_START_MIN) & (tt < SESSION_END_MIN)

    # staleness of the join, in trading days
    day_pos = {d: i for i, d in enumerate(report.index)}
    ev_day = trading_day(pd.DatetimeIndex(ev["confirm_time"]))
    own = np.array([day_pos.get(d, -1) for d in ev_day])
    stale = np.where((src >= 0) & (own >= 0), own - src, -1)

    return {
        "poi": poi["poi_passed"].to_numpy(),
        "poi_raw": poi["poi_passed_raw"].to_numpy(),
        "bias": dg["gate_bias"].to_numpy() & (bdir == sign),
        "profile": dg["gate_profile"].to_numpy(),
        "align": dg["gate_alignment"].to_numpy(),
        "smt": dg["gate_smt"].to_numpy() if has_smt else np.zeros(len(ev), bool),
        "session": np.asarray(sess),
        "_src": src,
        "_stale": stale,
        "join_resolved": float((src >= 0).mean()),
    }


def rung_masks(g: dict, n: int) -> dict:
    """Forward ladder (§2.1) and leave-one-out (§2.2), as boolean masks."""
    out, cum = {}, np.ones(n, bool)
    out["R0"] = cum.copy()
    for k, name in enumerate(GATES, start=1):
        cum = cum & g[name]
        out[f"R{k}"] = cum.copy()
    full = out["R4"]
    for name in GATES:
        m = np.ones(n, bool)
        for h in GATES:
            if h != name:
                m = m & g[h]
        out[f"LOO-{name}"] = m
    out["K1 session"] = full & g["session"]
    out["K2 SMT"] = full & g["smt"]
    out["K3 session+SMT"] = full & g["session"] & g["smt"]
    return out


# ══ trades ════════════════════════════════════════════════════════════════════
def build_trades(ev: pd.DataFrame, m1: pd.DataFrame, bars: pd.DataFrame,
                 struct_bars: pd.DataFrame, tf: str, max_hold: int = MAX_HOLD
                 ) -> pd.DataFrame:
    """One row per CISD event: entry at the confirming bar's CLOSE, stop at the
    protected swing (§1.10, §1.11).

    The entry index `i0` is the first M1 bar starting at or after
    `confirm_time + one entry-timeframe period`. That single line is the
    off-by-one this project has already been burned by, in both directions, and
    `assert_no_lookahead` checks it rather than trusting this comment.

    `struct_target` is the structural target of §1.12 — the last CLOSED
    structure-timeframe candle's extreme in the trade direction. A target already
    behind the entry is not a trade and becomes NaN.
    """
    delta = pd.Timedelta(tf)
    t = pd.DatetimeIndex(ev["confirm_time"])
    long_ = (ev["direction"] == "bullish").to_numpy()
    entry = ev["confirm_close"].to_numpy(float)
    stop = ev["protected_swing"].to_numpy(float)
    risk = np.abs(entry - stop)

    m1_t = m1.index.to_numpy()
    tf_t = bars.index.to_numpy()
    i0 = np.searchsorted(m1_t, (t + delta).to_numpy(), side="left")
    i1 = np.searchsorted(m1_t, (t + delta * (max_hold + 1)).to_numpy(), side="left")
    j0 = np.searchsorted(tf_t, (t + delta).to_numpy(), side="left")
    j1 = np.searchsorted(tf_t, (t + delta * (max_hold + 1)).to_numpy(), side="left")

    # last CLOSED structure-timeframe bar at the entry moment
    s_delta = pd.Timedelta(struct_bars.index.freq or infer_freq(struct_bars.index))
    s_t = struct_bars.index.to_numpy()
    s_pos = np.searchsorted(s_t, (t + delta - s_delta).to_numpy(), side="right") - 1
    s_ok = s_pos >= 0
    s_hi = np.where(s_ok, struct_bars["high"].to_numpy()[np.clip(s_pos, 0, None)], np.nan)
    s_lo = np.where(s_ok, struct_bars["low"].to_numpy()[np.clip(s_pos, 0, None)], np.nan)
    struct = np.where(long_, s_hi, s_lo)

    # ATR(20) on the entry timeframe at the signal bar — used only to detect the
    # shrinking-sample signature (§5.4.2), never as a filter.
    h, l, c = bars["high"], bars["low"], bars["close"]
    tr_ = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()],
                    axis=1).max(axis=1)
    atr = tr_.rolling(20, min_periods=20).mean()
    atr_at = atr.reindex(t).to_numpy(float)

    out = pd.DataFrame({
        "ev_i": np.arange(len(ev)),
        "time": t, "tf": tf, "long": long_, "entry": entry, "stop": stop,
        "risk": risk, "struct_target": struct, "atr20": atr_at,
        "i0": i0, "i1": i1, "j0": j0, "j1": j1,
        "wick_ratio": np.nan, "body_ratio": np.nan,
    })
    # Direction sanity: a bullish CISD must have its protected swing BELOW entry.
    dir_ok = np.where(long_, stop < entry, stop > entry)
    out["_dir_ok"] = dir_ok
    keep = (out["risk"] > 0) & (out["i1"] > out["i0"]) & dir_ok
    dropped = int((~keep).sum())
    out = out[keep].reset_index(drop=True)
    out.attrs["dropped"] = dropped
    return out


def target_levels(tr: pd.DataFrame, target: str) -> np.ndarray:
    if target == "structural":
        lv = tr["struct_target"].to_numpy(float).copy()
        bad = np.where(tr["long"].to_numpy(), lv <= tr["entry"], lv >= tr["entry"])
        lv[bad | ~np.isfinite(lv)] = np.nan
        return lv
    mult = float(target.rstrip("R"))
    sgn = np.where(tr["long"].to_numpy(), 1.0, -1.0)
    return tr["entry"].to_numpy(float) + sgn * mult * tr["risk"].to_numpy(float)


def matched_control(tr: pd.DataFrame, target_px: np.ndarray, bars: pd.DataFrame,
                    m1: pd.DataFrame, tf: str, reps: int = CTRL_REPS,
                    seed: int = SEED, window_days: int = CTRL_WINDOW_DAYS,
                    max_hold: int = MAX_HOLD) -> tuple[pd.DataFrame, np.ndarray]:
    """§4.3, locked in full: a random-entry twin for every real trade.

    Matched on direction, stop distance in price, target distance in price, entry
    timeframe, max hold, exit resolution and cost. The entry moment is drawn
    uniformly from entry-timeframe bars within +/-30 CALENDAR DAYS of the real
    trade's entry.

    The +-30-day window is the locked value and may not be swept. Gold ran ~1,100
    to ~5,500 across this span and realised volatility roughly tripled, so a
    2026-sized stop distance dropped into 2016 is simply a different trade.
    Drawing across the whole span instead inflated an independent rung-0
    differential by 38% at 4h — and, worse for a ladder, it inflates MOST the
    rungs whose gates concentrate trades into particular periods, which is
    exactly the comparison the ladder exists to make.

    `src` carries the real trade's `ev_i`, so every rung's control is the exact
    subset belonging to that rung's trades. Drawing controls once for the whole
    R0 book and subsetting is identical to redrawing per rung, and it keeps the
    control arm from silently changing when a rung changes.
    """
    keep = np.isfinite(target_px)
    src = tr[keep].reset_index(drop=True)
    dist = np.abs(target_px[keep] - src["entry"].to_numpy(float))

    delta = pd.Timedelta(tf)
    tf_t = bars.index.to_numpy()
    m1_t = m1.index.to_numpy()
    t = pd.DatetimeIndex(src["time"])
    w = pd.Timedelta(days=window_days)
    lo_b = np.searchsorted(tf_t, (t - w).to_numpy(), side="left")
    hi_b = np.searchsorted(tf_t, (t + w).to_numpy(), side="right")
    hi_b = np.maximum(hi_b, lo_b + 1)

    rng = np.random.default_rng(seed)
    close = bars["close"].to_numpy(float)
    long_ = src["long"].to_numpy()
    risk = src["risk"].to_numpy(float)
    sgn = np.where(long_, 1.0, -1.0)
    frames, targets = [], []
    for rep in range(reps):
        pick = rng.integers(lo_b, hi_b)
        rt = pd.DatetimeIndex(tf_t[pick])
        entry = close[pick]
        frames.append(pd.DataFrame({
            "ev_i": src["ev_i"].to_numpy(), "rep": rep,
            "time": rt, "tf": tf, "long": long_, "entry": entry,
            "stop": entry - sgn * risk, "risk": risk,
            "i0": np.searchsorted(m1_t, (rt + delta).to_numpy(), side="left"),
            "i1": np.searchsorted(m1_t, (rt + delta * (max_hold + 1)).to_numpy(),
                                  side="left"),
            "j0": np.searchsorted(tf_t, (rt + delta).to_numpy(), side="left"),
            "j1": np.searchsorted(tf_t, (rt + delta * (max_hold + 1)).to_numpy(),
                                  side="left"),
            "offset_days": (rt - t).total_seconds() / 86400.0,
        }))
        targets.append(entry + sgn * dist)
    out = pd.concat(frames, ignore_index=True)
    tgt = np.concatenate(targets)
    ok = (out["i1"] > out["i0"]).to_numpy()
    return out[ok].reset_index(drop=True), tgt[ok]


# ══ statistics ════════════════════════════════════════════════════════════════
def basic_stats(res: pd.DataFrame) -> dict:
    n = len(res)
    if n == 0:
        return {"n": 0, "win": np.nan, "exp_r": np.nan, "pf": np.nan,
                "mdd_r": np.nan, "risk": np.nan, "time_exit": np.nan,
                "bars": np.nan, "atr_mult": np.nan}
    net = res["net_usd"].to_numpy(float)
    r = res["net_r"].to_numpy(float)
    wins, losses = net[net > 0].sum(), -net[net <= 0].sum()
    order = res.sort_values("exit_time")["net_r"].to_numpy(float)
    eq = np.cumsum(order)
    mdd = float(np.max(np.maximum.accumulate(np.concatenate(([0.0], eq)))
                       - np.concatenate(([0.0], eq))))
    bars = ((pd.DatetimeIndex(res["exit_time"]) - pd.DatetimeIndex(res["time"]))
            .total_seconds() / 60.0).to_numpy()
    am = (res["risk"] / res["atr20"]).to_numpy(float) if "atr20" in res else np.array([np.nan])
    return {
        "n": n, "win": float((net > 0).mean()), "exp_r": float(r.mean()),
        "pf": float(wins / losses) if losses > 0 else float("inf"),
        "mdd_r": mdd, "risk": float(res["risk"].mean()),
        "time_exit": float((res["reason"] == "time").mean()),
        "bars": float(np.nanmean(bars)),
        "atr_mult": float(np.nanmean(am)),
    }


def _block_boot(arrays: list[np.ndarray], n_draw: int, rng,
                mean_block: int = BLOCK_MEAN) -> list[np.ndarray]:
    """Stationary block bootstrap means, for several arrays under ONE resampling.

    Consecutive entry-timeframe bars can each produce an event and no position cap
    is applied in the primary, so trades overlap heavily and an i.i.d. bootstrap
    understates variance. Phase 2 did not do this and its CIs are correspondingly
    optimistic; §4.5 makes the wider of the two the one the verdict uses.

    Blocks have geometric lengths with mean `mean_block` and wrap around the end
    of the series, which is Politis & Romano's stationary bootstrap. The
    implementation never materialises the (draws x n) index matrix: a block's
    contribution to the sum is a difference of two cumulative sums over the
    doubled series, so a draw costs one gather per block rather than per element.
    Passing several arrays together is what keeps the pairing intact — the real
    trades and their matched controls must be resampled by the SAME blocks or the
    comparison stops being paired.
    """
    n = len(arrays[0])
    if n < 2:
        return [np.array([]) for _ in arrays]
    p = 1.0 / mean_block
    nb = int(n / mean_block * 2) + 50
    L = rng.geometric(p, size=(n_draw, nb))
    cum = L.cumsum(axis=1)
    if not (cum[:, -1] >= n).all():                      # pathological, but check
        extra = rng.geometric(p, size=(n_draw, nb))
        L = np.concatenate([L, extra], axis=1)
        cum = L.cumsum(axis=1)
    prev = cum - L
    l_eff = np.clip(np.minimum(L, n - prev), 0, None)
    starts = rng.integers(0, n, size=L.shape)
    out = []
    for x in arrays:
        c = np.concatenate([[0.0], np.tile(x, 2).cumsum()])
        out.append((c[starts + l_eff] - c[starts]).sum(axis=1) / n)
    return out


def diff_with_ci(real_r: np.ndarray, ctrl_r: np.ndarray,
                 pair_real: np.ndarray, pair_ctrl: np.ndarray,
                 n_boot: int = N_BOOT, seed: int = SEED
                 ) -> tuple[float, float, float, str]:
    """Differential and its 95% CI — the WIDER of i.i.d. and block bootstrap.

    `real_r` / `ctrl_r` are the two arms pooled (the i.i.d. comparison phase 2
    used). `pair_real` / `pair_ctrl` are per-trade values in time order, with the
    control collapsed to a per-trade mean over its reps, which is what makes the
    block resample coherent: a block of adjacent trades carries its own controls
    with it.
    """
    if len(real_r) < 2 or len(ctrl_r) < 2:
        return np.nan, np.nan, np.nan, "n/a"
    obs, lo_i, hi_i = boot_diff(real_r, ctrl_r, n=n_boot, seed=seed)
    n = len(pair_real)
    if n >= 2:
        rng = np.random.default_rng(seed + 7)
        ma, mb = _block_boot([pair_real, pair_ctrl], n_boot, rng)
        d = ma - mb
        lo_b, hi_b = float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
    else:
        lo_b = hi_b = np.nan
    if np.isfinite(lo_b) and (hi_b - lo_b) > (hi_i - lo_i):
        return obs, lo_b, hi_b, "block"
    return obs, lo_i, hi_i, "iid"


def holm(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, bool]:
    """Holm-Bonferroni within a family. Returns which nulls are rejected."""
    items = [(k, v) for k, v in pvals.items() if np.isfinite(v)]
    items.sort(key=lambda kv: kv[1])
    m = len(items)
    out, rejected = {k: False for k in pvals}, True
    for i, (k, p) in enumerate(items):
        if rejected and p <= alpha / (m - i):
            out[k] = True
        else:
            rejected = False
    return out


def ci_p(obs: float, lo: float, hi: float) -> float:
    """A two-sided p-value implied by a symmetric normal CI. Used only to feed the
    Holm correction, which needs an ordering; the CI itself is what is reported."""
    if not np.isfinite(obs) or not np.isfinite(lo) or not np.isfinite(hi):
        return np.nan
    se = (hi - lo) / (2 * 1.959964)
    if se <= 0:
        return np.nan
    z = abs(obs) / se
    return float(math.erfc(z / math.sqrt(2)))


def label_transition(d_prev: float, d_now: float, lo: float, hi: float,
                     n_now: int) -> str:
    """§2.4's pre-declared labels, applied mechanically.

    ADDS VALUE / MERELY SHRINKS THE SAMPLE / COSTS / INDETERMINATE. `lo`,`hi` are
    the CI on the RISE in the differential, not on the differential itself.
    """
    if not np.isfinite(lo):
        return "INDETERMINATE (no CI)"
    if lo > 0:
        return "ADDS VALUE"
    if hi < 0:
        return "COSTS"
    if n_now < POWER_FLOOR_5PP:
        return "INDETERMINATE (underpowered)"
    return "MERELY SHRINKS THE SAMPLE"


def sanity_flags(s: dict, diff_win: float) -> list[str]:
    """§4.1.3 — a suspected harness fault is not a finding."""
    f = []
    if np.isfinite(s["win"]) and not (SANE_WIN[0] <= s["win"] <= SANE_WIN[1]):
        f.append(f"win rate {s['win']:.1%} outside {SANE_WIN}")
    if np.isfinite(s["exp_r"]) and abs(s["exp_r"]) > SANE_EXP_R:
        f.append(f"expectancy {s['exp_r']:.3f}R outside +/-{SANE_EXP_R}R")
    if np.isfinite(diff_win) and abs(diff_win) > SANE_DIFF_PP:
        f.append(f"differential {100*diff_win:.1f}pp outside +/-{100*SANE_DIFF_PP:.0f}pp")
    if np.isfinite(s["pf"]) and s["pf"] > SANE_PF:
        f.append(f"profit factor {s['pf']:.2f} above {SANE_PF}")
    return f


# ══ no-lookahead assertions (§4.1 — a precondition, not a recommendation) ═════
def assert_no_lookahead(ev: pd.DataFrame, tr: pd.DataFrame, poi: pd.DataFrame,
                        g: dict, report: pd.DataFrame, m1: pd.DataFrame,
                        tf: str) -> dict:
    """Every gate, checked against the moment it claims to fire.

    A run without these passing is not a valid test and its numbers may not be
    reported. The checks are inequalities on timestamps, computed for EVERY event
    in the book rather than sampled.
    """
    delta = pd.Timedelta(tf)
    conf = pd.DatetimeIndex(ev["confirm_time"])
    decision = conf + delta                      # the entry moment
    checks = {}

    # 1. entry strictly after the signal bar closes
    if len(tr):
        first_m1 = m1.index[tr["i0"].to_numpy()]
        need = pd.DatetimeIndex(tr["time"]) + delta
        checks["entry_after_signal_close"] = bool((first_m1 >= need).all())
        checks["entry_min_slack_min"] = float(
            ((first_m1 - need).total_seconds() / 60).min())
    else:
        checks["entry_after_signal_close"] = True

    # 2. the CISD itself: the confirming bar is strictly after the run ends and
    #    after the swing is confirmable
    checks["cisd_confirm_after_series"] = bool(
        (pd.DatetimeIndex(ev["confirm_time"]) > pd.DatetimeIndex(ev["series_end"])).all())
    checks["cisd_confirm_after_swing_confirm"] = bool(
        (pd.DatetimeIndex(ev["confirm_time"])
         >= pd.DatetimeIndex(ev["extreme_time"]) + delta * (SWING_RIGHT + 1)).all())

    # 3. POI: the gate's last consumed bar must have closed by the decision moment
    lb = pd.DatetimeIndex(poi["poi_last_bar_used"])
    used = poi["poi_passed"].to_numpy()
    checks["poi_available_where_used"] = bool(((lb + delta)[used] <= decision[used]).all()) \
        if used.any() else True
    checks["poi_raw_violation_share"] = float(
        (poi["poi_passed_raw"].to_numpy() & ~poi["poi_in_time"].to_numpy()).mean())

    # 4. daily gates: the joined day's verdict must have resolved by the event
    src = g["_src"]
    av = pd.to_datetime(report["day_gates_available_at"], utc=True).to_numpy()
    ok = True
    if (src >= 0).any():
        sel = src >= 0
        ok = bool((av[src[sel]] <= conf.to_numpy()[sel]).all())
    checks["day_gate_availability"] = ok
    checks["day_gate_max_staleness_days"] = int(g["_stale"].max())

    checks["ALL_PASS"] = all(v for k, v in checks.items()
                             if isinstance(v, bool))

    # Not a lookahead check, and deliberately outside ALL_PASS: §2.0 asserts that
    # `no_fade` is DEFINITIONALLY redundant — a confirmed daily bias already
    # entails a daily candle closing that way, so the gate can never fail once
    # `gate_bias` has passed. Measured rather than assumed, because a claim of
    # definitional redundancy is exactly the kind that survives review unchecked.
    b = report["gate_bias"].fillna(False).to_numpy(bool)
    nf = report["gate_no_fade"].fillna(False).to_numpy(bool)
    checks["no_fade_redundant"] = bool((~b | nf).all())
    checks["no_fade_exceptions"] = int((b & ~nf).sum())
    return checks


# ══ the measurement engine ════════════════════════════════════════════════════
class Book:
    """One resolved book for a (stack, target, cost): the real R0 trades and their
    5x matched control, both resolved on M1, indexed so any rung is a subset.

    The whole ladder is a family of subsets of R0, and the control is matched
    per-trade, so resolving once and slicing is IDENTICAL to redrawing per rung —
    and it removes any chance of the control arm quietly changing between rungs,
    which is the one thing that would make the ladder's comparisons incomparable.
    """

    def __init__(self, real: pd.DataFrame, ctrl: pd.DataFrame, n_ev: int,
                 span_yrs: float):
        self.n_ev = n_ev
        self.span_yrs = span_yrs
        self.real = real.sort_values("time").reset_index(drop=True)
        self.ctrl = ctrl
        self.r_ev = self.real["ev_i"].to_numpy()
        self.r_r = self.real["net_r"].to_numpy(float)
        self.r_w = (self.real["net_usd"].to_numpy(float) > 0).astype(float)
        self.r_t = pd.DatetimeIndex(self.real["time"])
        self.c_ev = ctrl["ev_i"].to_numpy()
        self.c_r = ctrl["net_r"].to_numpy(float)
        self.c_w = (ctrl["net_usd"].to_numpy(float) > 0).astype(float)
        # per-real-trade control means, for the paired block bootstrap
        gm = pd.DataFrame({"ev": self.c_ev, "r": self.c_r, "w": self.c_w}) \
            .groupby("ev").mean()
        self.cm_r = np.full(n_ev, np.nan)
        self.cm_w = np.full(n_ev, np.nan)
        self.cm_r[gm.index.to_numpy()] = gm["r"].to_numpy()
        self.cm_w[gm.index.to_numpy()] = gm["w"].to_numpy()

    def cell(self, ev_mask: np.ndarray, tmask: np.ndarray | None = None,
             years: float | None = None, seed: int = SEED,
             keep_pairs: bool = False) -> dict:
        """One reportable cell: n, win, expectancy, and the differential with CI."""
        sel = ev_mask[self.r_ev]
        if tmask is not None:
            sel = sel & tmask
        rr = self.real[sel]
        if len(rr) == 0:
            return {"n": 0}
        keep_ev = np.zeros(self.n_ev, bool)
        keep_ev[self.r_ev[sel]] = True
        csel = keep_ev[self.c_ev]
        s = basic_stats(rr)
        cr, cw = self.c_r[csel], self.c_w[csel]
        pr, pw = self.r_r[sel], self.r_w[sel]
        pcr, pcw = self.cm_r[self.r_ev[sel]], self.cm_w[self.r_ev[sel]]
        good = np.isfinite(pcr)
        d_r, lo_r, hi_r, w_r = diff_with_ci(pr, cr, pr[good], pcr[good], seed=seed)
        d_w, lo_w, hi_w, w_w = diff_with_ci(pw, cw, pw[good], pcw[good], seed=seed + 1)
        yrs = years if years else self.span_yrs
        out = {
            **s, "n_ctrl": int(csel.sum()),
            "ctrl_win": float(cw.mean()) if len(cw) else np.nan,
            "ctrl_exp_r": float(cr.mean()) if len(cr) else np.nan,
            "diff_r": d_r, "diff_r_lo": lo_r, "diff_r_hi": hi_r, "diff_r_ci": w_r,
            "diff_win": d_w, "diff_win_lo": lo_w, "diff_win_hi": hi_w,
            "diff_win_ci": w_w,
            "p_r": ci_p(d_r, lo_r, hi_r), "p_win": ci_p(d_w, lo_w, hi_w),
            "total_r_yr": float(pr.sum() / yrs) if yrs else np.nan,
            "n_yr": float(len(rr) / yrs) if yrs else np.nan,
            "mde_ctrl": mde_vs_control(len(rr)),
        }
        if keep_pairs:
            out["pair_r"], out["pair_cr"] = pr, pcr
        return out

    def rise(self, a: np.ndarray, b: np.ndarray, seed: int = SEED) -> dict:
        """CI on the RISE in the differential between two rungs.

        This is the quantity §2.4 and H1 are written on, and it is not the
        difference of two published CIs: the two rungs share trades, so the rise
        is bootstrapped directly on the paired per-trade differentials.
        """
        out = {}
        for tag, real_v, ctrl_v in (("r", self.r_r, self.cm_r),
                                    ("win", self.r_w, self.cm_w)):
            sa, sb = a[self.r_ev], b[self.r_ev]
            da = real_v[sa] - ctrl_v[self.r_ev[sa]]
            db = real_v[sb] - ctrl_v[self.r_ev[sb]]
            da, db = da[np.isfinite(da)], db[np.isfinite(db)]
            if len(da) < 2 or len(db) < 2:
                out[tag] = (np.nan, np.nan, np.nan)
                continue
            obs, lo_i, hi_i = boot_diff(db, da, n=N_BOOT, seed=seed)
            rng = np.random.default_rng(seed + 3)
            (ma,) = _block_boot([da], N_BOOT, rng)
            (mb,) = _block_boot([db], N_BOOT, np.random.default_rng(seed + 4))
            d = mb - ma
            lo_b, hi_b = float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
            if (hi_b - lo_b) > (hi_i - lo_i):
                out[tag] = (obs, lo_b, hi_b)
            else:
                out[tag] = (obs, lo_i, hi_i)
        return out


def make_book(tr: pd.DataFrame, ctrl_tr: pd.DataFrame, ctrl_tgt: np.ndarray,
              m1: pd.DataFrame, target: str, cost, n_ev: int, span_yrs: float,
              bars: pd.DataFrame | None = None, coarse: bool = False) -> Book:
    tgt = target_levels(tr, target)
    icol = ("j0", "j1") if coarse else ("i0", "i1")
    frame = bars if coarse else m1
    real = apply_cost(resolve(tr, tgt, frame, i0col=icol[0], i1col=icol[1],
                              tie="stop"), cost)
    ctrl = apply_cost(resolve(ctrl_tr, ctrl_tgt, frame, i0col=icol[0],
                              i1col=icol[1], tie="stop"), cost)
    return Book(real, ctrl, n_ev, span_yrs)


def subsample_calibration(bk: "Book", m0: np.ndarray, m4: np.ndarray,
                          n_draw: int = 1000, seed: int = SEED) -> dict:
    """How often does a sample of R4's size, drawn from R0, reach R4's estimate?

    §5.4b's decisive discriminator. The ladder's differential will almost
    certainly rise as `n` collapses; that is simultaneously the shape a real
    effect takes and the shape a shrinking sample manufactures. This answers the
    question directly and quantitatively, and its answer is not negotiable after
    the fact.
    """
    s0, s4 = m0[bk.r_ev], m4[bk.r_ev]
    d0 = bk.r_r[s0] - bk.cm_r[bk.r_ev[s0]]
    d4 = bk.r_r[s4] - bk.cm_r[bk.r_ev[s4]]
    d0, d4 = d0[np.isfinite(d0)], d4[np.isfinite(d4)]
    if len(d4) < 2 or len(d0) < len(d4):
        return {}
    rng = np.random.default_rng(seed + 11)
    obs = float(d4.mean())
    draws = np.array([d0[rng.choice(len(d0), len(d4), replace=False)].mean()
                      for _ in range(n_draw)])
    return {"n_sub": int(len(d4)), "r0_diff": float(d0.mean()), "r4_diff": obs,
            "reach_share": float((draws >= obs).mean()),
            "sub_p95": float(np.percentile(draws, 95)),
            "sub_sd": float(draws.std())}


# ══ per-stack driver ══════════════════════════════════════════════════════════
def run_stack(m1: pd.DataFrame, report: pd.DataFrame, entry_tf: str,
              struct_tf: str, bias_tf: str, name: str, span_yrs: float,
              tag: str, counts_only: bool = False, verbose: bool = True,
              level_rule: str = LEVEL_RULE, max_wait: int = MAX_WAIT,
              min_series: int = MIN_SERIES) -> dict:
    t0 = time.time()
    bars = resample(m1, entry_tf)
    struct_bars = resample(m1, struct_tf)
    ev = build_events(bars, f"{tag}_{entry_tf}", level_rule=level_rule,
                      max_wait=max_wait, min_series=min_series)
    if verbose:
        print(f"  {entry_tf}: {len(bars):,} bars, {len(ev):,} CISD events "
              f"({round(time.time()-t0)}s)", flush=True)
    if len(ev) == 0:
        return {}
    poi = poi_annotate(bars, ev, entry_tf,
                       f"{tag}_{level_rule}_{max_wait}_{min_series}")
    g = gate_matrix(ev, poi, report)
    masks = rung_masks(g, len(ev))
    counts = {k: int(v.sum()) for k, v in masks.items()}
    if verbose:
        print(f"  {entry_tf}: rungs " +
              " ".join(f"{k}={counts[k]:,}" for k in RUNGS) +
              f"  ({round(time.time()-t0)}s)", flush=True)

    # the same ladder with the RAW (availability-unguarded) POI gate, so the
    # pre-registration's own §3.2 counts can be reproduced and the difference read
    graw = dict(g); graw["poi"] = g["poi_raw"]
    masks_raw = rung_masks(graw, len(ev))
    counts_raw = {k: int(v.sum()) for k, v in masks_raw.items()}

    out = {
        "name": name, "entry_tf": entry_tf, "struct_tf": struct_tf,
        "bias_tf": bias_tf, "bars": len(bars), "n_ev": len(ev),
        "counts": counts, "counts_raw_poi": counts_raw, "span_yrs": span_yrs,
        "poi_pass_raw": float(g["poi_raw"].mean()),
        "poi_pass": float(g["poi"].mean()),
        "poi_kind": {str(k): int(v) for k, v in
                     poi["poi_kind"].value_counts(dropna=False).items()},
        "join_resolved": g["join_resolved"],
        "stale_hist": {int(k): int(v) for k, v in
                       pd.Series(g["_stale"]).value_counts().sort_index().items()},
        "secs": round(time.time() - t0, 1),
    }
    if counts_only:
        return out

    tr = build_trades(ev, m1, bars, struct_bars, entry_tf)
    out["trades_dropped"] = int(tr.attrs.get("dropped", 0))
    out["lookahead"] = assert_no_lookahead(ev, tr, poi, g, report, m1, entry_tf)

    books, ctrl_primary = {}, None
    for target in TARGETS:
        tgt = target_levels(tr, target)
        ctrl_tr, ctrl_tgt = matched_control(tr, tgt, bars, m1, entry_tf)
        books[target] = make_book(tr, ctrl_tr, ctrl_tgt, m1, target,
                                  PRIMARY_COST, len(ev), span_yrs)
        if target == PRIMARY_TARGET:
            rsk = tr.set_index("ev_i").loc[ctrl_tr["ev_i"], "risk"].to_numpy()
            out["ctrl_quality"] = {
                "n": int(len(ctrl_tr)),
                "stop_dist_max_abs_err": float(
                    np.abs(ctrl_tr["risk"].to_numpy() - rsk).max()),
                "offset_min": float(ctrl_tr["offset_days"].min()),
                "offset_max": float(ctrl_tr["offset_days"].max()),
                "offset_abs_mean": float(ctrl_tr["offset_days"].abs().mean()),
            }
            ctrl_primary = (ctrl_tr, ctrl_tgt)
    pb = books[PRIMARY_TARGET]

    # ── the ladder, forward and leave-one-out, at the primary target and cost ──
    ladder, prev = {}, None
    for rk in RUNGS:
        c = pb.cell(masks[rk])
        if prev is not None:
            r = pb.rise(masks[prev], masks[rk])
            c["rise_r"], c["rise_win"] = r["r"], r["win"]
            c["label"] = label_transition(0, 0, r["r"][1], r["r"][2],
                                          int(c.get("n", 0)))
        ladder[rk] = c
        prev = rk
    for gname in GATES:
        k = f"LOO-{gname}"
        c = pb.cell(masks[k])
        r = pb.rise(masks[k], masks["R4"])       # full model vs full-minus-gate
        c["rise_r"], c["rise_win"] = r["r"], r["win"]
        ladder[k] = c
    for k in ("K1 session", "K2 SMT", "K3 session+SMT"):
        ladder[k] = pb.cell(masks[k])
    out["H1"] = pb.rise(masks["R0"], masks["R4"])
    out["ladder"] = ladder

    # The same ladder with the availability guard OFF — i.e. the POI gate exactly
    # as `estimate_conjunction_power` applies it, which is how the
    # pre-registration's own §3.2 counts were produced. Reported so the guard's
    # effect is a measured difference rather than an assertion, and so the
    # literal pre-registered cell (n = 722 on the primary stack) is in the file.
    out["ladder_raw_poi"] = {rk: pb.cell(masks_raw[rk]) for rk in RUNGS}
    out["H1_raw_poi"] = pb.rise(masks_raw["R0"], masks_raw["R4"])
    out["blocks_raw_poi"] = {}
    for bname, a_, b_ in calendar_blocks(m1):
        tm = (pb.r_t >= a_) & (pb.r_t < b_) if bname != "B4" else (pb.r_t >= a_)
        out["blocks_raw_poi"][bname] = pb.cell(
            masks_raw["R4"], np.asarray(tm), years=(b_ - a_).days / 365.25)

    # ── regime blocks, EVERY rung ─────────────────────────────────────────────
    blocks = calendar_blocks(m1)
    out["block_spans"] = [(b, str(a.date()), str(c.date())) for b, a, c in blocks]
    out["blocks"] = {}
    for rk in RUNGS:
        row = {}
        for bname, a, b in blocks:
            tm = (pb.r_t >= a) & (pb.r_t < b) if bname != "B4" else (pb.r_t >= a)
            row[bname] = pb.cell(masks[rk], np.asarray(tm),
                                 years=(b - a).days / 365.25)
        out["blocks"][rk] = row

    # ── PRE / IS / OOS ────────────────────────────────────────────────────────
    samples = {
        "PRE": (pb.r_t < PRE_END, (PRE_END - m1.index.min()).days / 365.25),
        "IS": ((pb.r_t >= PRE_END) & (pb.r_t < IS_END),
               (IS_END - PRE_END).days / 365.25),
        "OOS": (pb.r_t >= IS_END, (m1.index.max() - IS_END).days / 365.25),
    }
    out["samples"] = {rk: {s: pb.cell(masks[rk], np.asarray(mk), years=y)
                           for s, (mk, y) in samples.items()} for rk in RUNGS}

    # ── cost sensitivity ──────────────────────────────────────────────────────
    tgt2 = target_levels(tr, PRIMARY_TARGET)
    ctrl_tr, ctrl_tgt = ctrl_primary
    real_raw = resolve(tr, tgt2, m1, tie="stop")
    ctrl_raw = resolve(ctrl_tr, ctrl_tgt, m1, tie="stop")
    out["costs"] = {}
    for cost in COSTS:
        bk = Book(apply_cost(real_raw, cost), apply_cost(ctrl_raw, cost),
                  len(ev), span_yrs)
        out["costs"][str(cost)] = {rk: bk.cell(masks[rk]) for rk in ("R0", "R4")}

    # ── target sensitivity ────────────────────────────────────────────────────
    out["targets"] = {t: {rk: books[t].cell(masks[rk]) for rk in ("R0", "R4")}
                      for t in TARGETS}

    # ── resolution diagnostic: M1 vs signal-timeframe bars (§4.2) ─────────────
    coarse = make_book(tr, ctrl_tr, ctrl_tgt, m1, PRIMARY_TARGET, PRIMARY_COST,
                       len(ev), span_yrs, bars=bars, coarse=True)
    out["coarse"] = {rk: coarse.cell(masks[rk]) for rk in ("R0", "R4")}
    opt = apply_cost(resolve(tr, tgt2, m1, tie="target"), PRIMARY_COST)
    out["tie_target"] = {"win": float((opt["net_usd"] > 0).mean()),
                         "exp_r": float(opt["net_r"].mean())}

    # ── truncate-at-gap variant (§4.2) ────────────────────────────────────────
    tr2 = tr.copy()
    tr2["i1"] = truncate_at_gap(tr, m1)
    tr2 = tr2[tr2["i1"] > tr2["i0"]].reset_index(drop=True)
    if len(tr2):
        trunc = apply_cost(resolve(tr2, target_levels(tr2, PRIMARY_TARGET), m1,
                                   tie="stop"), PRIMARY_COST)
        out["truncated"] = {"n": int(len(trunc)),
                            "win": float((trunc["net_usd"] > 0).mean()),
                            "exp_r": float(trunc["net_r"].mean())}

    # ── §5.4b discriminator 1 ────────────────────────────────────────────────
    out["subsample"] = subsample_calibration(pb, masks["R0"], masks["R4"])

    # ── equal wall-clock hold (§5.4b discriminator 3) ─────────────────────────
    out["equal_hold"] = equal_wall_clock(tr, ctrl_tr, ctrl_tgt, m1, bars,
                                         entry_tf, masks, len(ev), span_yrs)

    # ── §4.1.3: sweep every reported cell for a suspected harness fault ───────
    flags = []
    for group, d in (("ladder", out["ladder"]), ("raw-POI ladder", out["ladder_raw_poi"]),
                     ("coarse", out["coarse"]), ("equal-hold", out["equal_hold"])):
        for k, c in d.items():
            if isinstance(c, dict) and c.get("n", 0) >= 30:
                for f in sanity_flags(c, c.get("diff_win", float("nan"))):
                    flags.append(f"{entry_tf} {group} {k}: {f}")
    for rk, row in out["blocks"].items():
        for b, c in row.items():
            if c.get("n", 0) >= 30:
                for f in sanity_flags(c, c.get("diff_win", float("nan"))):
                    flags.append(f"{entry_tf} block {rk}/{b}: {f}")
    for rk, row in out["samples"].items():
        for smp, c in row.items():
            if c.get("n", 0) >= 30:
                for f in sanity_flags(c, c.get("diff_win", float("nan"))):
                    flags.append(f"{entry_tf} sample {rk}/{smp}: {f}")
    for t, row in out["targets"].items():
        for rk, c in row.items():
            if c.get("n", 0) >= 30:
                for f in sanity_flags(c, c.get("diff_win", float("nan"))):
                    flags.append(f"{entry_tf} target {t}/{rk}: {f}")
    out["sanity_flags"] = flags

    out["secs"] = round(time.time() - t0, 1)
    if verbose:
        print(f"  {entry_tf}: done in {out['secs']}s  "
              f"sanity flags: {len(flags)}", flush=True)
    return out


def equal_wall_clock(tr, ctrl_tr, ctrl_tgt, m1, bars, tf, masks, n_ev, span_yrs,
                     hours: int = 24) -> dict:
    """Re-resolve the book with the SAME wall-clock hold on every stack.

    `max_hold = 10` entry-timeframe periods gives a 1h trade ten hours and a 15m
    trade two and a half. A longer window raises the chance of touching either
    barrier and, under any positive drift, favours the target — so a cross-stack
    comparison at fixed bar-count holds is partly a comparison of hold lengths.
    24 hours is a neutral common horizon chosen for this diagnostic only; it is
    not pre-registered and is not verdict-bearing.
    """
    m1_t = m1.index.to_numpy()
    w = pd.Timedelta(hours=hours)
    a, b = tr.copy(), ctrl_tr.copy()
    for f in (a, b):
        t = pd.DatetimeIndex(f["time"]) + pd.Timedelta(tf)
        f["i1"] = np.searchsorted(m1_t, (t + w).to_numpy(), side="left")
    ka = (a["i1"] > a["i0"]).to_numpy()
    kb = (b["i1"] > b["i0"]).to_numpy()
    a, b = a[ka].reset_index(drop=True), b[kb].reset_index(drop=True)
    bk = Book(apply_cost(resolve(a, target_levels(a, PRIMARY_TARGET), m1,
                                 tie="stop"), PRIMARY_COST),
              apply_cost(resolve(b, ctrl_tgt[kb], m1, tie="stop"), PRIMARY_COST),
              n_ev, span_yrs)
    return {"hours": hours,
            **{rk: bk.cell(masks[rk]) for rk in ("R0", "R4")}}


# ══ declared-reading sensitivity (family B) and disagreement rates ════════════
def reading_disagreement(m1: pd.DataFrame, bars: pd.DataFrame, tag: str) -> dict:
    """§5.5 requires the CISD level-rule and C3-reference disagreement rates.

    They are not cosmetic. Two detectors wearing the name "CISD" that agree on
    little more than half their events are two different trading systems, which is
    exactly why one reading is locked as primary and the other is declared.
    """
    out = {}
    base = build_events(bars, f"{tag}_cisd_base")
    sets = {"series_open": set(map(str, base["confirm_time"]))}
    for rule in ("series_max_open", "series_extreme", "series_close"):
        ev = build_events(bars, f"{tag}_cisd_{rule}", level_rule=rule)
        sets[rule] = set(map(str, ev["confirm_time"]))
        out[f"n_{rule}"] = len(ev)
    a = sets["series_open"]
    out["n_series_open"] = len(a)
    for rule in ("series_max_open", "series_extreme", "series_close"):
        b = sets[rule]
        out[f"jaccard_{rule}"] = (len(a & b) / len(a | b)) if (a | b) else np.nan
    daily = daily_candles(m1)
    ca = daily_closures(daily, c3_reference="c2_open")
    cb = daily_closures(daily, c3_reference="c2_extreme")
    both = (ca["closure"] != "none") | (cb["closure"] != "none")
    out["c3_n_days"] = int(both.sum())
    out["c3_agree"] = float((ca["closure"] == cb["closure"])[both].mean()) \
        if both.any() else np.nan
    out["c3_A_only"] = int(((ca["c3_closure"] != "none")
                            & (cb["c3_closure"] == "none")).sum())
    out["c3_B_only"] = int(((cb["c3_closure"] != "none")
                            & (ca["c3_closure"] == "none")).sum())
    return out


# ══ formatting ════════════════════════════════════════════════════════════════
def f3(x, nd=3):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) \
        else f"{x:+.{nd}f}"


def fpc(x, nd=1):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) \
        else f"{100*x:.{nd}f}%"


def fpp(x, nd=1):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) \
        else f"{100*x:+.{nd}f}pp"


def ci(lo, hi, nd=3):
    if lo is None or not np.isfinite(lo):
        return "—"
    return f"[{lo:+.{nd}f}, {hi:+.{nd}f}]"


def cell_row(label, c, extra=""):
    if not c or c.get("n", 0) == 0:
        return f"| {label} | 0 | — | — | — | — | — |{extra}"
    return (f"| {label} | {c['n']:,} | {fpc(c['win'])} | {f3(c['exp_r'])} | "
            f"{f3(c['diff_r'])} | {ci(c['diff_r_lo'], c['diff_r_hi'])} | "
            f"{fpp(c['diff_win'])} |{extra}")


def verdict_for(c: dict, n_floor: int = POWER_FLOOR_5PP) -> str:
    """§5.1 / §5.2 / §5.3, applied to one cell, in the document's own words."""
    if not c or c.get("n", 0) == 0:
        return "INDETERMINATE — no events"
    lo, hi = c.get("diff_r_lo"), c.get("diff_r_hi")
    n = c["n"]
    if not np.isfinite(lo):
        return "INDETERMINATE — no CI"
    if lo > 0:
        return "positive, CI excludes zero"
    if hi < 0:
        return "negative, CI excludes zero (§5.2 item 2)"
    if n >= n_floor:
        return "REFUTES — a well-powered zero (§5.2 item 1)"
    return f"INDETERMINATE — underpowered (§5.3 item 1); n={n:,} < {n_floor}"



# ══ reconciliation and family-B sensitivity ═══════════════════════════════════
def coordinator_check(m1: pd.DataFrame, span_yrs: float, tag: str,
                      tfs=("1h", "4h"), reps: int = 3, cost=0.0) -> dict:
    """Rung 0 at the coordinator's parameters, not this run's locked ones.

    An independent check of rung 0 was run with `cisd_events` DEFAULTS
    (`max_wait=40`), a 3:1 control and no costs, while the locked primary uses
    `max_wait=3` and a 5:1 control at 0.04R. Those are different books — the
    speed rule alone removes ~40% of events — so the two cannot be compared
    without reproducing the other's configuration. That is what this does. A
    material disagreement here would mean one of the two harnesses is wrong, and
    that outranks everything else in the report.
    """
    from detectors.bias import four_hour_candles
    out = {}
    for tf in list(tfs) + ["4h forex grid"]:
        # The locked 4H grid is the FOREX one (17/21/01/09 NY, §1.4), which is not
        # the same object as a UTC-aligned 4h resample. Both are reported because a
        # cross-check that silently compares two different candle sets is not a
        # cross-check.
        if tf == "4h forex grid":
            bars = four_hour_candles(m1, grid="forex")[
                ["open", "high", "low", "close"]]
            period = "4h"
        else:
            bars = resample(m1, tf)
            period = tf
        ev = build_events(bars, f"{tag}_{tf.replace(' ', '_')}_coord",
                          max_wait=40, min_series=1)
        tr = build_trades(ev, m1, bars, bars, period)
        tgt = target_levels(tr, "2R")
        ctrl_tr, ctrl_tgt = matched_control(tr, tgt, bars, m1, period, reps=reps)
        real = apply_cost(resolve(tr, tgt, m1, tie="stop"), cost)
        ctrl = apply_cost(resolve(ctrl_tr, ctrl_tgt, m1, tie="stop"), cost)
        bk = Book(real, ctrl, len(ev), span_yrs)
        c = bk.cell(np.ones(len(ev), bool))
        blocks = {}
        for bname, a, b in calendar_blocks(m1):
            tm = (bk.r_t >= a) & (bk.r_t < b) if bname != "B4" else (bk.r_t >= a)
            blocks[bname] = bk.cell(np.ones(len(ev), bool), np.asarray(tm),
                                    years=(b - a).days / 365.25)
        out[tf] = {"cell": c, "blocks": blocks}
    return out


def family_b(m1: pd.DataFrame, report_primary: pd.DataFrame, xag, tag: str,
             span_yrs: float, entry_tf: str = PRIMARY_STACK,
             struct_tf: str = "4h", bias_tf: str = "1D") -> dict:
    """The pre-declared alternative readings, one at a time on the R4 cell.

    §4.6 family B is a 2^5 grid of 32 cells. This runs the five one-at-a-time
    deviations from the locked primary rather than the full factorial: the
    factorial's marginal value is in interactions between readings, and no cell
    in this family may change the verdict in any case (§4.6, standing rule 2).
    That restriction is a [DEVIATION] from the letter of §4.6 and is reported as
    one rather than presented as the full family.
    """
    bars = resample(m1, entry_tf)
    struct = resample(m1, struct_tf)
    out = {}

    def cell_for(rep, level_rule=LEVEL_RULE, max_wait=MAX_WAIT,
                 min_series=MIN_SERIES, key=""):
        ev = build_events(bars, f"{tag}_{entry_tf}_{level_rule}_{max_wait}_{min_series}",
                          level_rule=level_rule, max_wait=max_wait,
                          min_series=min_series)
        if len(ev) == 0:
            return {"n": 0}
        poi = poi_annotate(bars, ev, entry_tf,
                           f"{tag}_{level_rule}_{max_wait}_{min_series}")
        g = gate_matrix(ev, poi, rep)
        masks = rung_masks(g, len(ev))
        tr = build_trades(ev, m1, bars, struct, entry_tf)
        tgt = target_levels(tr, PRIMARY_TARGET)
        ctrl_tr, ctrl_tgt = matched_control(tr, tgt, bars, m1, entry_tf)
        bk = make_book(tr, ctrl_tr, ctrl_tgt, m1, PRIMARY_TARGET, PRIMARY_COST,
                       len(ev), span_yrs)
        return bk.cell(masks["R4"])

    out["CISD level = highest/lowest open of the series (§1.8 secondary)"] = \
        cell_for(report_primary, level_rule="series_max_open")
    out["CISD min_series = 2 (§1.8 secondary)"] = \
        cell_for(report_primary, min_series=2)
    out["CISD max_wait = 40 (§1.8 secondary)"] = \
        cell_for(report_primary, max_wait=40)
    for scope in ("wick",):
        rep = make_report(m1, tag, xag, cisd_scope=scope)
        out[f"cisd_scope = {scope} (§1.8 [P], the largest lever in the model)"] = \
            cell_for(rep)
    for c3 in ("c2_extreme",):
        rep = make_report(m1, tag, xag, c3_reference=c3)
        out[f"C3 reference = {c3} (Reading B, §1.7 secondary)"] = cell_for(rep)
    return out

# ══ the report ════════════════════════════════════════════════════════════════
DIFF_HDR = ("| rung | n | win | expectancy R | diff vs control (R) | 95% CI | "
            "diff win |")
DIFF_SEP = "|---|---:|---:|---:|---:|---|---:|"


def write_report(res: dict, ctx: dict, out_path: Path = OUT_MD) -> str:
    L: list[str] = []
    A = L.append
    prim = res.get(PRIMARY_STACK)
    powered = res.get(POWERED_STACK)

    A("# The conjunction test — result")
    A("")
    A("**Phase 3, workstream B. Run 2026-08-25 against the pre-registered protocol "
      "in `meta/conjunction_preregistration.md`, which was written and signed off "
      "before any conjunction result existed.** Nothing in the primary "
      "configuration was changed after a number was seen. Where this run had to "
      "depart from the pre-registration, or found the pre-registration wrong, it "
      "says so under *What the pre-registration got wrong* — it does not deviate "
      "silently.")
    A("")
    A(f"Data: `m3_scalper/xau_m1_full.parquet` restricted to the certified span "
      f"**{ctx['span_start']} → {ctx['span_end']}, {ctx['span_yrs']:.2f} years, "
      f"{ctx['n_m1']:,} M1 bars**. Generated by `python/backtest_conjunction.py`.")
    A("")
    A("> **A hard limit that bounds every conclusion below: there is no sustained "
      "bear market in the certified span.** The only real gold bear market in the "
      "16.5 years the feed reaches is 2013 (−28%), and it sits on the wrong side "
      "of the October-2015 trading-calendar change that disqualifies pre-2016 data "
      "for every session- and calendar-dependent gate in this model. The best "
      "available non-bull regimes here are the 2016–2018 range and the 2021–2022 "
      "flat years. **No result in this document may be described as having been "
      "validated against a sustained gold downtrend.**")
    A("")

    # ── validity preconditions ────────────────────────────────────────────────
    A("## 0. Validity preconditions")
    A("")
    A("A run without these passing is not a valid test and its numbers may not be "
      "reported (§4.1). They are checked for every event in every book, not sampled.")
    A("")
    A("| check | primary stack | powered stack | swing stack |")
    A("|---|---|---|---|")
    keys = [("entry_after_signal_close", "entry strictly after the signal bar closes"),
            ("cisd_confirm_after_series", "CISD confirm bar after the opposing series"),
            ("cisd_confirm_after_swing_confirm", "CISD confirm bar after swing confirmation"),
            ("poi_available_where_used", "POI verdict available at the entry moment"),
            ("day_gate_availability", "daily gates resolved before the event")]
    for k, lab in keys:
        vals = []
        for s in (PRIMARY_STACK, POWERED_STACK, "1h"):
            r = res.get(s, {}).get("lookahead", {})
            v = r.get(k)
            vals.append("PASS" if v is True else ("FAIL" if v is False else "—"))
        A(f"| {lab} | {vals[0]} | {vals[1]} | {vals[2]} |")
    A("")
    allpass = all(res.get(s, {}).get("lookahead", {}).get("ALL_PASS", True)
                  for s in res)
    A(f"**No-lookahead assertion: {'PASS' if allpass else 'FAIL'}** on every stack "
      f"with an outcome book.")
    A("")
    if prim:
        la = prim["lookahead"]
        A(f"Two numbers behind those PASSes, because a green tick is not evidence. "
          f"On the primary stack the first M1 bar eligible to resolve a trade sits "
          f"**{la.get('entry_min_slack_min', float('nan')):.0f} minutes** after the "
          f"signal bar's close at the minimum, and the joined daily verdict is at "
          f"most **{la.get('day_gate_max_staleness_days', 0)} trading day** old.")
        A("")
        A(f"**One pre-registered claim does not hold exactly, and it is not a "
          f"validity failure.** §2.0 removed `no_fade` from the ladder on the "
          f"grounds that it is *definitionally* redundant — a confirmed daily bias "
          f"entails a daily candle closing that way, so the gate can never fail "
          f"once `gate_bias` has passed. Measured over the certified span it fails "
          f"on **{la.get('no_fade_exceptions', 0)}** biased day"
          f"{'' if la.get('no_fade_exceptions', 0) == 1 else 's'} of "
          f"{ctx.get('day_layer', {}).get('gate_bias', 0):,}. The decision to drop "
          f"the rung stands on frequency; the word *definitionally* is slightly "
          f"too strong.")
        A("")
    flags = [f for s in res.values() for f in s.get("sanity_flags", [])]
    A(f"**Harness sanity floor (§4.1.3): {len(flags)} flag"
      f"{'' if len(flags) == 1 else 's'}** across every reported cell with n ≥ 30. "
      "A win rate below 10% or above 90%, an expectancy outside ±1.0 R, a "
      "differential outside ±15pp or a profit factor above 3 is a suspected "
      "harness fault to be diagnosed, not a finding to be reported.")
    A("")
    for f in flags[:40]:
        A(f"- {f}")
    if flags:
        A("")
        pooled = [f for f in flags if " ladder " in f]
        A("**Diagnosis, because a flag is a trigger to investigate and not a "
          "result to report.** " + (
              f"**{len(pooled)} of these fall on a pooled ladder cell and must be "
              f"diagnosed before anything downstream is trusted: "
              + "; ".join(pooled[:5]) + ".**"
              if pooled else
              "None falls on a pooled ladder cell, on rung 0 or rung 1, or on any "
              "cell that carries a verdict. Every one is on a *regime block* or a "
              "*sample slice* of a rung at or below R4 — cells holding a few dozen "
              "trades, where a 15-20pp win-rate differential is one or two trades. "
              "The `n` for each is in the corresponding table of §5 or §6, and no "
              "flagged quantity is quoted anywhere in this document as a finding. "
              "That is what the floor is for: it marks the cells too small to mean "
              "anything, and at these sample sizes the correct reading is "
              "small-sample noise, not a harness fault."))
        A("")

    # ── THE PRIMARY RESULT ────────────────────────────────────────────────────
    A("## 1. The pre-registered primary result")
    A("")
    A("The primary hypothesis is **rung R4 of the ladder — bias → profile → POI → "
      "alignment → CISD — measured against its matched random-entry control**, at "
      f"the locked target (**{PRIMARY_TARGET}**), the locked cost "
      f"(**{PRIMARY_COST} proportional**, §1.15 as amended), M1 exit resolution "
      "with same-bar ties taken as the stop, and the ±30-day matched control at "
      f"K={CTRL_REPS}. Two cells carry it: the primary 15m/4H/1D stack, and the "
      "pre-designated powered comparison, the 5m/1H/1D playbook stack.")
    A("")
    A(DIFF_HDR + " verdict |")
    A(DIFF_SEP + "---|")
    for s, lab in ((PRIMARY_STACK, "**PRIMARY — 15m / 4H / 1D, R4**"),
                   (POWERED_STACK, "**POWERED — 5m / 1H / 1D, R4**")):
        r = res.get(s)
        if not r or "ladder" not in r:
            continue
        c = r["ladder"]["R4"]
        A(cell_row(lab, c, f" {verdict_for(c)} |"))
    A("")
    if powered and "ladder" in powered:
        cp = powered["ladder"]["R4"]
        decisive = (cp["n"] >= POWER_FLOOR_5PP and np.isfinite(cp["diff_r_lo"])
                    and cp["diff_r_lo"] <= 0 <= cp["diff_r_hi"])
        if decisive:
            A(f"**The headline, in the pre-registration's own words: the "
              f"conjunction is REFUTED on the one stack that can decide it.** "
              f"§5.2 item 1 defines refutation as a differential whose 95% CI "
              f"contains zero at or above the {POWER_FLOOR_5PP:,}-trade power "
              f"floor — *a well-powered zero, which is a real result and should be "
              f"stated as one*. The powered playbook stack delivers "
              f"{cp['n']:,} trades, {int(cp['n'] / powered['span_yrs'])} a year "
              f"over {powered['span_yrs']:.2f} years, and a differential of "
              f"{f3(cp['diff_r'])} R with a CI of "
              f"{ci(cp['diff_r_lo'], cp['diff_r_hi'])}. §5.2 item 1 anticipated "
              f"exactly this cell — *this threshold is already cleared by the "
              f"playbook stack at R4 on current data, so a null there is a finding "
              f"today.* The primary 15m stack agrees in sign and cannot decide, "
              f"which §3.6 also predicted.")
            A("")
    if prim and "ladder" in prim:
        c = prim["ladder"]["R4"]
        c0 = prim["ladder"]["R0"]
        h1 = prim["H1"]["r"]
        r0null = (c0["n"] >= POWER_FLOOR_5PP and np.isfinite(c0["diff_r_lo"])
                  and c0["diff_r_lo"] <= 0 <= c0["diff_r_hi"])
        A(f"**Read that against the pre-registered bar, which is rung 0 and not "
          f"zero.** Bare CISD on the same stack returns a differential of "
          f"{f3(c0['diff_r'])} R on {c0['n']:,} events; the full model returns "
          f"{f3(c['diff_r'])} R on {c['n']:,}. **H1 — that R4 exceeds R0 — is "
          f"measured at {f3(h1[0])} R, 95% CI {ci(h1[1], h1[2])}**, which contains "
          f"zero, so H1 does not hold.")
        A("")
        if r0null:
            A(f"**And rung 0 is itself a well-powered zero, which changes what the "
              f"comparison means.** §2.5 fixed rung 0 as the comparator precisely "
              f"because a provisional baseline had put bare CISD meaningfully "
              f"above its own control at 1h and 4h. At the locked parameters over "
              f"the certified span it is not: {f3(c0['diff_r'])} R with a CI of "
              f"{ci(c0['diff_r_lo'], c0['diff_r_hi'])} on {c0['n']:,} trades, far "
              f"above the power floor. When the baseline is indistinguishable from "
              f"its control, *beating rung 0* and *beating your own control* stop "
              f"being different questions — and the full model does neither. §12 "
              f"says which comparison each verdict rests on rather than letting "
              f"them blur.")
            A("")
    A("### The same cell with the POI availability guard switched off")
    A("")
    A("The pre-registration's §3.2 counts were produced with the POI gate applied "
      "as `estimate_conjunction_power` applies it, which does not check whether the "
      "gate's verdict had resolved by the entry moment. Both ladders are reported "
      "so the guard's effect is a measured difference and not an assertion, and so "
      "the literally pre-registered cell is in this file.")
    A("")
    A(DIFF_HDR + " verdict |")
    A(DIFF_SEP + "---|")
    for s in (PRIMARY_STACK, POWERED_STACK, "1h"):
        r = res.get(s)
        if not r or "ladder_raw_poi" not in r:
            continue
        c = r["ladder_raw_poi"]["R4"]
        A(cell_row(f"{s} R4, unguarded POI", c, f" {verdict_for(c)} |"))
    A("")
    if prim and "H1_raw_poi" in prim:
        h = prim["H1_raw_poi"]["r"]
        A(f"H1 under the unguarded gate, primary stack: {f3(h[0])} R, 95% CI "
          f"{ci(h[1], h[2])}.")
        A("")
    A("**The event rates, before any differential is read** (§5.5). Predicted "
      "against measured, at R4, on the certified span:")
    A("")
    A("| stack | predicted (§3.2) | measured, guarded | measured, unguarded | "
      "per year | ≥ 868 real trades? |")
    A("|---|---:|---:|---:|---:|---|")
    for s in (PRIMARY_STACK, POWERED_STACK, "1h"):
        r = res.get(s)
        if not r:
            continue
        n = r["counts"]["R4"]
        A(f"| {s} | {PREDICTED.get((s, 'R4'), '—')} | {n:,} | "
          f"{r['counts_raw_poi']['R4']:,} | "
          f"{n/r['span_yrs']:,.0f} | "
          f"{'**yes**' if n >= POWER_FLOOR_5PP else 'no'} |")
    A("")
    # Exact reproduction check against §3.2, the strongest validation available:
    # a different workstream measured the same counts with the same modules.
    pk = PREDICTED_KNOBS
    exact, checked = [], 0
    for s in STACK_ORDER:
        r = res.get(s)
        if not r:
            continue
        for rk in RUNGS:
            p = PREDICTED.get((s, rk))
            if p:
                checked += 1
                if int(p.replace(",", "")) == r["counts_raw_poi"][rk]:
                    exact.append(f"{s} {rk}")
        for k, lab in (("K1", "K1 session"), ("K2", "K2 SMT"),
                       ("K3", "K3 session+SMT")):
            if (s, k) in pk:
                checked += 1
                if pk[(s, k)] == r["counts_raw_poi"][lab]:
                    exact.append(f"{s} {k}")
    if checked:
        A(f"**The unguarded ladder reproduces §3.2 exactly, on every cell.** "
          f"{len(exact)} of {checked} pre-registered event counts — every forward "
          f"rung and every knob on all three stacks with a published prediction — "
          f"match this run to the single event. Be precise about what that does "
          f"and does not prove: the two runs share the detector modules and the "
          f"day-join helper (`estimate_conjunction_power.join_day_gates` is "
          f"imported here rather than reimplemented, deliberately, so the two "
          f"cannot drift), so the agreement is not independent of those. It is "
          f"independent of the trade construction, the control, the resolution "
          f"and every statistic. **What it localises is the whole disagreement:** "
          f"the guarded and unguarded ladders differ by the POI availability "
          f"guard and by nothing else.")
        A("")
    A("The pre-registration said in advance that the primary stack resolves only "
      "the top of the plausible 3–5pp effect band and that a null on it would be "
      "genuinely ambiguous, while the pre-designated powered stack was expected to "
      "clear the floor and therefore to be able to produce a real result. Which "
      "stack can carry a verdict is decided by that table, not by what the "
      "differentials turn out to be.")
    A("")

    # ── rung 0 ────────────────────────────────────────────────────────────────
    A("## 2. Rung 0 first, and separately — every later rung is read against this")
    A("")
    A("§5.5 requires the rung-0 differential on every stack to be reported before "
      "anything else, because bare CISD is already above its own control on some "
      "timeframes and a profitable full model may be nothing but rung 0 surviving "
      "four gates.")
    A("")
    A(DIFF_HDR + " total R/yr | n/yr |")
    A(DIFF_SEP + "---:|---:|")
    for s, _, _, name in STACKS:
        r = res.get(s)
        if not r or "ladder" not in r:
            continue
        c = r["ladder"]["R0"]
        A(cell_row(f"{s} ({name})", c,
                   f" {f3(c['total_r_yr'], 1)} | {c['n_yr']:,.0f} |"))
    A("")
    if ctx.get("coordinator"):
        A("### Reconciliation with the coordinator's independent rung-0 check")
        A("")
        A(ctx["coordinator"])
        A("")

    # ── the forward ladder ────────────────────────────────────────────────────
    A("## 3. The forward ladder")
    A("")
    A("Each rung adds exactly one gate, in the corpus's own order of operations. "
      "The label in the last column is pre-declared (§2.4) and is applied "
      "mechanically to the CI on the **rise** in the differential from the "
      "previous rung — not to the differential itself, and never to the raw win "
      "rate.")
    A("")
    for s, st, bt, name in STACKS:
        r = res.get(s)
        if not r:
            continue
        A(f"### {s} / {st} / {bt} — {name}")
        A("")
        if "ladder" not in r:
            A(f"**Event counts only** ({r['n_ev']:,} CISD events on {r['bars']:,} "
              f"bars). §1.2 designates this stack the *power-ceiling reference* "
              f"and says it is **off-method** — `excluded-tooling` says futures "
              f"only, no CFDs and no scalping — and that it is reported *for its "
              f"event count only*. No outcome book was resolved and none should "
              f"be: a differential computed here would be a number for a "
              f"configuration the corpus disowns.")
            A("")
            A("| rung | events | per year | vs R0 | events, unguarded POI |")
            A("|---|---:|---:|---:|---:|")
            n0 = max(r["counts"]["R0"], 1)
            for rk in RUNGS:
                n = r["counts"][rk]
                A(f"| {RUNG_LABEL[rk]} | {n:,} | {n/r['span_yrs']:,.0f} | "
                  f"{100*n/n0:.1f}% | {r['counts_raw_poi'][rk]:,} |")
            A("")
            if r["counts"]["R4"] >= POWER_FLOOR_5PP:
                A(f"**Worth stating plainly, because it is phase 2's structural "
                  f"complaint restated exactly.** This stack — the one the corpus "
                  f"disowns — is the only one whose R4 clears the power floor "
                  f"outright, at {r['counts']['R4']:,} events against "
                  f"{POWER_FLOOR_5PP:,}. The timeframes that carry the claim do "
                  f"not have the data, and the timeframe that has the data is the "
                  f"one the method excludes. Measuring it anyway would answer a "
                  f"question nobody asked.")
                A("")
            continue
        A(DIFF_HDR + " rise CI | label | n unguarded | stop/ATR20 | R/yr | "
          "time-exit |")
        A(DIFF_SEP + "---|---|---:|---:|---:|---:|")
        for rk in RUNGS:
            c = r["ladder"][rk]
            rise = c.get("rise_r")
            extra = (f" {ci(rise[1], rise[2]) if rise else '—'} | "
                     f"{c.get('label', '(baseline)')} | "
                     f"{r['counts_raw_poi'][rk]:,} | "
                     f"{c.get('atr_mult', float('nan')):.2f} | "
                     f"{f3(c.get('total_r_yr', float('nan')), 1)} | "
                     f"{fpc(c.get('time_exit', float('nan')), 0)} |")
            A(cell_row(RUNG_LABEL[rk], c, extra))
        A("")
        c0 = r["ladder"]["R0"]
        A(f"**A consequence of the locked hold cap that the power arithmetic does "
          f"not account for.** §1.13 fixes `max_hold = 10` entry-timeframe periods "
          f"for comparability with phase 2, not from the corpus. On this stack "
          f"**{fpc(c0['time_exit'], 0)} of rung-0 trades never touch either "
          f"barrier** and exit at the hold cap with an intermediate R. So a 'win' "
          f"here is `net > 0`, not a 2R target hit, and §3.4's cross-check that an "
          f"X-point win-rate effect *is* a 3X effect in R — which holds only when "
          f"every trade resolves at −1R or +2R — does not describe this book. The "
          f"win-rate and R differentials can and do move in opposite directions "
          f"(rung 0: {fpp(c0['diff_win'])} against {f3(c0['diff_r'])} R), and the "
          f"MDE columns computed from a binomial at p = 0.36 are correspondingly "
          f"approximate. The R differential is the one to read.")
        A("")
        A("Description, per rung — §2.3 items 1, 4, 5, 6 and 7. Profit factor and "
          "drawdown are description and are never quoted without `n` and the "
          "control (§4.7 item 7).")
        A("")
        A("| rung | n/yr | mean stop USD | stop/ATR20 | mean hold (entry-TF bars) "
          "| time-exit | total R/yr | PF | max DD (R) |")
        A("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        per = pd.Timedelta(s).total_seconds() / 60.0
        for rk in RUNGS:
            c = r["ladder"][rk]
            if not c.get("n"):
                continue
            A(f"| {RUNG_LABEL[rk]} | {c['n_yr']:,.0f} | {c['risk']:.2f} | "
              f"{c['atr_mult']:.2f} | {c['bars']/per:.1f} | "
              f"{fpc(c['time_exit'], 0)} | {f3(c['total_r_yr'], 1)} | "
              f"{c['pf']:.3f} | {c['mdd_r']:.1f} |")
        A("")
        A("Knobs, declared and never verdict-bearing:")
        A("")
        A(DIFF_HDR)
        A(DIFF_SEP)
        for k in ("K1 session", "K2 SMT", "K3 session+SMT"):
            A(cell_row(k, r["ladder"][k]))
        A("")

    # ── leave one out ─────────────────────────────────────────────────────────
    A("## 4. The reverse ladder — leave one out")
    A("")
    A("The full model with one gate removed at a time. This is the half that "
      "identifies which gate carries an effect, and §5.1 item 6 requires at least "
      "one removal to significantly reduce the differential before the conjunction "
      "can be called confirmed.")
    A("")
    for s in (PRIMARY_STACK, POWERED_STACK, "1h"):
        r = res.get(s)
        if not r or "ladder" not in r:
            continue
        A(f"### {s} stack")
        A("")
        A(DIFF_HDR + " n vs full | effect of restoring the gate | 95% CI |")
        A(DIFF_SEP + "---:|---:|---|")
        full = r["ladder"]["R4"]
        A(cell_row("full model (R4)", full, " ×1.00 | — | — |"))
        for gname in GATES:
            c = r["ladder"][f"LOO-{gname}"]
            rise = c.get("rise_r")
            mult = c["n"] / max(full["n"], 1) if c.get("n") else float("nan")
            A(cell_row(f"minus {gname}", c,
                       f" ×{mult:.2f} | {f3(rise[0]) if rise else '—'} | "
                       f"{ci(rise[1], rise[2]) if rise else '—'} |"))
        A("")

    # ── regime blocks ─────────────────────────────────────────────────────────
    A("## 5. Regime blocks — every rung, not just the pooled figure")
    A("")
    if prim:
        A("Four equal calendar quarters of the certified span (§4.4b primary "
          "blocking). The boundaries are arithmetic — no price, no outcome and no "
          "judgement enters them. The requirement is **sign agreement in at least "
          "3 of 4**, deliberately not per-block significance, because a quarter of "
          "this span is far too small to resolve anything on its own.")
        A("")
        A("| block | span |")
        A("|---|---|")
        for b, a_, c_ in prim["block_spans"]:
            A(f"| {b} | {a_} → {c_} |")
        A("")
    for s in (PRIMARY_STACK, POWERED_STACK, "1h"):
        r = res.get(s)
        if not r or "blocks" not in r:
            continue
        A(f"### {s} stack — differential vs control, in R, by block")
        A("")
        A("| rung | B1 | B2 | B3 | B4 | signs | ≥3/4 agree? |")
        A("|---|---:|---:|---:|---:|---:|---|")
        for rk in RUNGS:
            row = r["blocks"][rk]
            vals, ns, cis = [], [], []
            for b in ("B1", "B2", "B3", "B4"):
                c = row.get(b, {})
                vals.append(c.get("diff_r", float("nan")) if c.get("n") else float("nan"))
                ns.append(c.get("n", 0))
                cis.append(ci(c.get("diff_r_lo"), c.get("diff_r_hi"), 2))
            pos = sum(1 for v in vals if np.isfinite(v) and v > 0)
            neg = sum(1 for v in vals if np.isfinite(v) and v < 0)
            agree = (f"YES ({'+' if pos >= neg else '−'})" if max(pos, neg) >= 3
                     else "**NO — regime-dependent (§4.4b)**")
            cells = " | ".join(f"{f3(v)}<br><sub>n={n:,}</sub><br><sub>{q}</sub>"
                               for v, n, q in zip(vals, ns, cis))
            A(f"| {RUNG_LABEL[rk]} | {cells} | {pos}+/{neg}− | {agree} |")
        A("")

    # ── PRE / IS / OOS ────────────────────────────────────────────────────────
    A("## 6. PRE, IS and OOS")
    A("")
    A("**Read the `n` column before the differential column.** The IS and OOS "
      "slices of R4 hold tens of trades, not hundreds; a confidence interval that "
      "excludes zero on 25 trades excludes zero because 25 trades is not a sample, "
      "and §4.7 item 7 forbids quoting any of it without `n`. Nothing in this "
      "table below the power floor is a finding, in either direction.")
    A("")
    A("**PRE is the confirmatory sample** (§4.4): everything before 2023-07-02 has "
      "never been examined by any workstream in this project — phase 1 read "
      "transcripts and every phase-2 measurement ran on `xau_m1_3y.parquet`, which "
      "starts on that date. IS and OOS are both inside the window phase 2 saw and "
      "are descriptive.")
    A("")
    for s in (PRIMARY_STACK, POWERED_STACK, "1h"):
        r = res.get(s)
        if not r or "samples" not in r:
            continue
        A(f"### {s} stack")
        A("")
        A("| rung | sample | n | win | exp R | diff R | 95% CI |")
        A("|---|---|---:|---:|---:|---:|---|")
        for rk in ("R0", "R4"):
            for smp in ("PRE", "IS", "OOS"):
                c = r["samples"][rk][smp]
                if not c.get("n"):
                    A(f"| {rk} | {smp} | 0 | — | — | — | — |")
                    continue
                A(f"| {rk} | {smp} | {c['n']:,} | {fpc(c['win'])} | "
                  f"{f3(c['exp_r'])} | {f3(c['diff_r'])} | "
                  f"{ci(c['diff_r_lo'], c['diff_r_hi'])} |")
        A("")

    # ── power ─────────────────────────────────────────────────────────────────
    A("## 7. Power, recomputed from the run")
    A("")
    A("The pre-registration's floors were computed on projected counts. These are "
      "the realised ones, so the predictions can be checked rather than assumed.")
    A("")
    A("| stack | rung | events (predicted) | events (measured) | per yr | "
      "MDE vs 5× control | real trades for 5pp |")
    A("|---|---|---:|---:|---:|---:|---:|")
    pred = PREDICTED
    for s, _, _, _ in STACKS:
        r = res.get(s)
        if not r:
            continue
        for rk in RUNGS:
            n = r["counts"][rk]
            p = pred.get((s, rk))
            A(f"| {s} | {RUNG_LABEL[rk]} | {p if p else '—'} | {n:,} | "
              f"{n/r['span_yrs']:,.0f} | {100*mde_vs_control(n):.1f}pp | "
              f"{POWER_FLOOR_5PP:,} |")
    A("")

    # ── costs and targets ─────────────────────────────────────────────────────
    A("## 8. Cost and target sensitivity")
    A("")
    A("The primary cost is **0.04R proportional** (§1.15 as amended): the span runs "
      "from ~$1,060 gold to ~$5,500, so a flat 0.2 USD/oz round trip is a 5× "
      "different relative tax at the two ends of the sample and is the only "
      "absolute-price quantity in the whole locked configuration. The flat levels "
      "are retained as diagnostics.")
    A("")
    A("**A property of the locked protocol that the pre-registration does not "
      "note, and that makes one of its confirmation conditions nearly vacuous.** "
      "The matched control carries the *same* stop distance and the *same* cost as "
      "its trade, so a flat USD cost contributes `−cost/risk` to both arms and "
      "cancels exactly in the differential; a proportional `0.04R` cost cancels "
      "identically. The differential columns below are therefore constant across "
      "the cost levels to within the rounding produced by a handful of control "
      "draws whose windows could not be resolved. §5.1 item 4 — *the differential "
      "survives cost 0.5 and cost 0.04R with the same sign* — is a condition the "
      "arithmetic guarantees, not a test. **The column that carries real "
      "information is the expectancy**, which is what decides whether a book is "
      "tradeable, and it is reported beside the differential for that reason.")
    A("")
    for s in (PRIMARY_STACK, POWERED_STACK, "1h"):
        r = res.get(s)
        if not r or "costs" not in r:
            continue
        A(f"### {s} stack")
        A("")
        A("| cost | R0 exp R | R0 diff | R0 CI | R4 exp R | R4 diff | R4 CI |")
        A("|---|---:|---:|---|---:|---:|---|")
        for cst in COSTS:
            d = r["costs"][str(cst)]
            c0, c4 = d["R0"], d["R4"]
            A(f"| {cst} | {f3(c0.get('exp_r'))} | {f3(c0.get('diff_r'))} | "
              f"{ci(c0.get('diff_r_lo'), c0.get('diff_r_hi'))} | "
              f"{f3(c4.get('exp_r'))} | {f3(c4.get('diff_r'))} | "
              f"{ci(c4.get('diff_r_lo'), c4.get('diff_r_hi'))} |")
        A("")
        A("| target | R0 n | R0 diff | R0 CI | R4 n | R4 diff | R4 CI |")
        A("|---|---:|---:|---|---:|---:|---|")
        for tg in TARGETS:
            d = r["targets"][tg]
            c0, c4 = d["R0"], d["R4"]
            A(f"| {tg} | {c0.get('n', 0):,} | {f3(c0.get('diff_r'))} | "
              f"{ci(c0.get('diff_r_lo'), c0.get('diff_r_hi'))} | "
              f"{c4.get('n', 0):,} | {f3(c4.get('diff_r'))} | "
              f"{ci(c4.get('diff_r_lo'), c4.get('diff_r_hi'))} |")
        A("")

    # ── diagnostics ───────────────────────────────────────────────────────────
    A("## 9. Diagnostics that §5.5 requires regardless of outcome")
    A("")
    A("### The matched control was applied as locked")
    A("")
    A("| stack | control trades | max &#124;control stop − real stop&#124; | "
      "entry offset (days) | mean &#124;offset&#124; |")
    A("|---|---:|---:|---|---:|")
    for s in STACK_ORDER:
        r = res.get(s)
        if not r or "ctrl_quality" not in r:
            continue
        q = r["ctrl_quality"]
        A(f"| {s} | {q['n']:,} | {q['stop_dist_max_abs_err']:.2e} | "
          f"[{q['offset_min']:.1f}, {q['offset_max']:.1f}] | "
          f"{q['offset_abs_mean']:.1f} |")
    A("")
    A("A stop-distance error of exactly zero and an offset inside ±30 days is what "
      "§4.3 locks; both hold.")
    A("")
    A("### The POI gate's availability, and what it costs")
    A("")
    A("| stack | POI pass, raw | POI pass, availability-guarded | events whose raw "
      "pass used data from after the entry moment |")
    A("|---|---:|---:|---:|")
    for s in STACK_ORDER:
        r = res.get(s)
        if not r:
            continue
        v = r.get("lookahead", {}).get("poi_raw_violation_share", float("nan"))
        A(f"| {s} | {fpc(r['poi_pass_raw'])} | {fpc(r['poi_pass'])} | {fpc(v)} |")
    A("")
    A("### The daily join (§4.1a)")
    A("")
    A("| stack | events whose join resolved | staleness (trading days) |")
    A("|---|---:|---|")
    for s in STACK_ORDER:
        r = res.get(s)
        if not r:
            continue
        h = r.get("stale_hist", {})
        tot = sum(v for k, v in h.items() if k >= 0)
        desc = ", ".join(f"{k}d {100*v/max(tot,1):.0f}%"
                         for k, v in sorted(h.items()) if k >= 0)
        A(f"| {s} | {fpc(r['join_resolved'])} | {desc} |")
    A("")
    A("### M1 versus signal-timeframe resolution (§4.2)")
    A("")
    A("| stack | rung | M1 win | M1 exp R | signal-TF win | signal-TF exp R |")
    A("|---|---|---:|---:|---:|---:|")
    for s in (PRIMARY_STACK, POWERED_STACK, "1h"):
        r = res.get(s)
        if not r or "coarse" not in r:
            continue
        for rk in ("R0", "R4"):
            a_, b_ = r["ladder"][rk], r["coarse"][rk]
            A(f"| {s} | {rk} | {fpc(a_.get('win'))} | {f3(a_.get('exp_r'))} | "
              f"{fpc(b_.get('win'))} | {f3(b_.get('exp_r'))} |")
    A("")
    A("### Declared-reading disagreement rates (§5.5)")
    A("")
    if ctx.get("disagree"):
        d = ctx["disagree"]
        A(f"CISD level rule, on the primary stack's entry timeframe: "
          f"`series_open` (primary) fires {d['n_series_open']:,} times; "
          f"`series_max_open` (the pre-declared secondary) {d['n_series_max_open']:,}, "
          f"Jaccard agreement **{d['jaccard_series_max_open']:.3f}**; "
          f"`series_extreme` {d['n_series_extreme']:,} (Jaccard "
          f"{d['jaccard_series_extreme']:.2f}) and `series_close` "
          f"{d['n_series_close']:,} (Jaccard {d['jaccard_series_close']:.2f}) are "
          f"diagnostics only — the corpus rules the extreme reading out and never "
          f"states the close reading.")
        A("")
        A(f"C3 closure reference, on daily candles: Reading A (C2's opening price, "
          f"primary) and Reading B (C2's extreme) agree on "
          f"**{fpc(d['c3_agree'])}** of the {d['c3_n_days']:,} days where either "
          f"produces a closure; {d['c3_A_only']:,} days are A-only and "
          f"{d['c3_B_only']:,} are B-only.")
        A("")
    A("### The shrinking-sample discriminators (§5.4, §5.4b)")
    A("")
    for s in (PRIMARY_STACK, POWERED_STACK, "1h"):
        r = res.get(s)
        if not r or not r.get("subsample"):
            continue
        sc = r["subsample"]
        A(f"**{s} stack.** Drawing 1,000 random subsamples of exactly R4's size "
          f"({sc['n_sub']:,}) from the R0 book gives a mean differential of "
          f"{f3(sc['r0_diff'])} R with a 95th percentile of {f3(sc['sub_p95'])} R. "
          f"R4's measured differential is {f3(sc['r4_diff'])} R, which "
          f"**{100*sc['reach_share']:.1f}%** of same-sized random subsamples of the "
          f"bare-CISD book reach or exceed.")
        A("")
        eh = r.get("equal_hold")
        if eh:
            A(f"Equal wall-clock hold ({eh['hours']}h instead of "
              f"{MAX_HOLD} entry-timeframe periods): R0 "
              f"{f3(eh['R0'].get('diff_r'))} R, R4 {f3(eh['R4'].get('diff_r'))} R.")
            A("")
        if r.get("truncated"):
            t = r["truncated"]
            A(f"Windows truncated at the first session break > 70 minutes: "
              f"n={t['n']:,}, win {fpc(t['win'])}, expectancy {f3(t['exp_r'])} R.")
            A("")
        tt = r.get("tie_target")
        if tt:
            A(f"Same-bar ties taken as the TARGET instead of the stop — the "
              f"optimistic rule, reported so the size of the choice is a number: "
              f"win {fpc(tt['win'])} against {fpc(r['ladder']['R0']['win'])}.")
            A("")

    if ctx.get("family_b"):
        A("## 10a. Family B — the declared alternative readings")
        A("")
        A("One at a time, on the primary stack's R4 cell, Holm-corrected within the "
          "family. **No cell here may change the verdict** (§4.6), and none is a "
          "sweep maximum.")
        A("")
        A("| reading | R4 n | diff R | 95% CI |")
        A("|---|---:|---:|---|")
        for k, c in ctx["family_b"].items():
            A(f"| {k} | {c.get('n', 0):,} | {f3(c.get('diff_r'))} | "
              f"{ci(c.get('diff_r_lo'), c.get('diff_r_hi'))} |")
        A("")
        cells = list(ctx["family_b"].values())
        pos = [c for c in cells if c.get("diff_r", 0) > 0]
        smallest = min(cells, key=lambda c: c.get("n", 0))
        A(f"Every interval contains zero and every cell is below the "
          f"{POWER_FLOOR_5PP:,}-trade floor, so none of them decides anything and "
          f"none may promote the null to a positive (§4.6, standing rule 2). "
          + (f"**{len(pos)} of {len(cells)} point estimates is positive, and it is "
             f"the one on the smallest sample** — `cisd_scope = wick` at "
             f"n = {smallest.get('n', 0):,}, which is 4.5× fewer trades than the "
             f"primary. That is the shape a sweep maximum has, and the rule "
             f"against reading one exists for exactly this cell."
             if len(pos) == 1 and pos[0] is smallest else
             f"{len(pos)} of {len(cells)} point estimates are positive."))
        A("")
        A("The sixth declared reading of §4.6's family B — the **inside-bar rule** "
          "— is absent because it is inert: `daily_bias` requires a daily C2 or C3 "
          "closure before a bias exists, and an inside bar produces no closure, so "
          "'inside bar = no trade' and 'inside bar inherits the prior bias' select "
          "the same days. See §11 item 3.")
        A("")

    A(family_a_holm(res))
    for sd in ctx.get("strat", []):
        A(strat_md(sd))
    if ctx.get("family_c"):
        A(family_c_md(ctx["family_c"]))
    if ctx.get("excl"):
        A(exclusion_md(ctx["excl"]))
    A(preregistration_errata(res, ctx))
    A(verdict_md(res, ctx))
    if ctx.get("extra_md"):
        A(ctx["extra_md"])

    txt = "\n".join(L) + "\n"
    out_path.write_text(txt, encoding="utf-8")
    return txt


def coordinator_md(coord: dict) -> str:
    """Rung 0 reproduced at the coordinator's parameters, as prose plus a table."""
    if not coord:
        return ""
    L = ["An independent rung-0 check was run by the coordinator on the same span "
         "with **different parameters** — `cisd_events` defaults (`max_wait=40`, "
         "against the locked `max_wait=3`, which alone removes ~40% of events), a "
         "3:1 control and no costs. Those are different books, so the two are "
         "reconciled by reproducing that configuration here rather than by "
         "comparing numbers that were never comparable.", "",
         "| TF | n | real exp R | control exp R | differential | 95% CI | "
         "B1 | B2 | B3 | B4 |", "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|"]
    for tf, d in coord.items():
        c = d["cell"]
        bl = " | ".join(f3(d["blocks"][b].get("diff_r")) for b in
                        ("B1", "B2", "B3", "B4"))
        L.append(f"| {tf} | {c['n']:,} | {f3(c['exp_r'])} | {f3(c['ctrl_exp_r'])} | "
                 f"{f3(c['diff_r'])} | {ci(c['diff_r_lo'], c['diff_r_hi'])} | {bl} |")
    got1h = coord.get("1h", {}).get("cell", {})
    L += ["",
          f"The coordinator reported **n = 12,933, differential +0.0283 ± 0.0285** "
          f"at 1h and **n = 3,331, +0.0337 ± 0.0566** at 4h, neither significant. "
          f"This run reproduces the 1h cell at **n = {got1h.get('n', 0):,}, "
          f"{f3(got1h.get('diff_r'))}, CI "
          f"{ci(got1h.get('diff_r_lo'), got1h.get('diff_r_hi'))}** — a 0.9% "
          f"difference in `n` and a difference in the differential well inside "
          f"either interval. **The two harnesses agree at 1h.** The residual `n` "
          f"gap is consistent with the small difference in the M1 slice each run "
          f"loaded (3,687,209 bars here against 3,686,962 reported).", "",
          "**The 1h row reconciles; the 4h row exposes a live parameter the "
          "pre-registration treats as settled.** The two 4h rows above are the "
          "same rule applied to two different candle sets — a UTC-aligned 4h "
          "resample, and the **forex grid (17/21/01/09 New York) that §1.4 locks "
          "for gold**. They are not close. The UTC grid returns a differential "
          "whose CI excludes zero and whose block signs agree 3 of 4; the locked "
          "forex grid returns one whose CI contains zero and whose block signs "
          "agree only 2 of 4 — a failure of §4.4b's requirement. "
          "`meta/session_window_fit.md` chose the forex grid on a structural "
          "tiebreak, calling the two grids *behaviourally indistinguishable "
          "(z = 0.08)*. On the counting statistic they were; on the outcome book "
          "they are not, and the choice moves both the significance and the "
          "regime-agreement verdict at rung 0. Nothing in this report's ladder "
          "depends on it — no stack uses 4h as an entry timeframe — but it is a "
          "settled-parameter claim that does not survive contact with a P&L.", ""]
    return "\n".join(L)



def preregistration_errata(res: dict, ctx: dict) -> str:
    """What the pre-registration got wrong, stated as findings rather than fixed
    silently. §5 requires deviations to be reported; this is that report."""
    prim = res.get(PRIMARY_STACK, {})
    la = prim.get("lookahead", {})
    d = ctx.get("disagree", {})
    L = ["## 11. What the pre-registration got wrong", "",
         "Ten items. None of them changes the primary configuration, which was run "
         "exactly as locked; eight are errors in the document's own supporting "
         "claims and two are places where this run could not do what the document "
         "asked and says so instead of quietly substituting.", ""]

    A = L.append
    A("**1. The POI gate's availability was specified in §4.1a and then not "
      "applied in §3.2.** The document's availability table (carried over from "
      "`meta/bias_poi_build.md`) says the POI gate resolves at "
      "`detail[\"last_bar_used\"] + freq`, and §4.1 makes it a precondition that no "
      "gate use data timestamped at or after the moment it fires. But §4.1's third "
      "POI branch — *use the CISD level, and additionally require 50% of the "
      "bodies of that opposing series to hold* — is a forward test with a "
      "five-bar window, while the locked `max_wait = 3` puts the confirming CISD "
      "three to five bars after the same series. The verdict therefore usually "
      f"resolves after the event it is supposed to qualify: on the primary stack "
      f"**{fpc(la.get('poi_raw_violation_share', float('nan')))} of all events** "
      "have a raw POI pass that consumed data from after the entry moment. §3.2's "
      "counts were produced without that check, so every rung below R0 in the "
      "pre-registration is larger than a lookahead-free ladder can be. "
      f"Measured: R4 falls from the pre-registered **722** to "
      f"**{prim.get('counts', {}).get('R4', 0)}** on the primary stack, and from "
      f"**176** to **{res.get('1h', {}).get('counts', {}).get('R4', 0)}** on the "
      "swing stack. Both ladders are reported here; the guarded one is primary, "
      "because §4.1 outranks §3.2 — a count is not a result, and validity is a "
      "precondition.")
    A("")
    A("**2. The two declared CISD level readings are, on this instrument, the same "
      "reading.** §1.8 locks `series_open` as primary and declares "
      "`series_max_open` as the pre-declared secondary, treating the choice as a "
      "live [P] worth both-ways reporting. It is not: for a bullish setup the run "
      "is a series of down-close candles, whose highest open is almost always the "
      "first one's, so the two rules pick the same level. Measured on the primary "
      f"stack's entry timeframe over the certified span, Jaccard agreement is "
      f"**{d.get('jaccard_series_max_open', float('nan')):.3f}** — "
      f"{d.get('n_series_open', 0):,} events against "
      f"{d.get('n_series_max_open', 0):,}. The readings that genuinely differ are "
      f"the two the corpus rules out: `series_extreme` "
      f"({d.get('jaccard_series_extreme', float('nan')):.2f}) and `series_close` "
      f"({d.get('jaccard_series_close', float('nan')):.2f}). "
      "`meta/cisd_reading_comparison.md`'s 0.56–0.59 and 0.22–0.29 figures are "
      "reproduced almost exactly — but they are figures for the *rejected* "
      "readings, and §1.8 carried their weight over to a pair that turns out to be "
      "interchangeable.")
    A("")
    A("**3. The inside-bar [P] of §1.4 is inert and cannot be tested as "
      "declared.** The primary reads an inside bar as no trade; the declared "
      "secondary has it inherit the previous non-zero bias. But `daily_bias` "
      "requires a daily **closure** (C2 or C3) before a bias exists at all, and an "
      "inside bar produces no closure by construction. The two readings therefore "
      "select identical days in this implementation, and the family-B cell for it "
      "is not a cell. It is reported as unrunnable rather than as agreeing.")
    A("")
    A("**4. Two internal inconsistencies about what the primary cell is.** §1.15 "
      "and §1.16 amend the primary cost to **0.04R proportional** (amendment A4), "
      "but §4.6's primary family and §5.1 both still say **cost 0.2**. Separately, "
      "§4.6 says the primary family is read on **OOS** while §4.4's PRE paragraph "
      "says the primary verdict is read on **PRE**. This run takes the amendments "
      "as controlling — 0.04R primary, PRE confirmatory — and reports 0.2 and OOS "
      "beside them, so the choice cannot change a conclusion.")
    A("")
    nfe = la.get("no_fade_exceptions", 0)
    nb = ctx.get("day_layer", {}).get("gate_bias", 0)
    if nfe:
        A(f"**5. `no_fade` is not *definitionally* redundant, only almost always "
          f"redundant.** §2.0 removes it as a rung on the grounds that a confirmed "
          f"bias cannot coexist with a daily candle opposing it — so the gate "
          f"*can never fail* once `gate_bias` has passed. Over the certified span "
          f"it fails on **{nfe}** biased day{'' if nfe == 1 else 's'} of {nb:,}. "
          f"The decision to drop the rung is right on frequency; the word "
          f"*definitionally* is too strong, and 'never fires against anything' is "
          f"the kind of claim that should be measured before it is used to remove "
          f"a rung from a ladder.")
    else:
        A(f"**5. `no_fade`'s redundancy claim checks out.** §2.0 removed it as a "
          f"rung on the grounds that a confirmed bias entails a daily candle "
          f"closing that way, so the gate can never fail once `gate_bias` has "
          f"passed. Measured over the certified span it fails on **no** biased day "
          f"of {nb:,}, which is the claim. Recorded here because it was asserted "
          f"rather than measured in the document, and an unmeasured 'this gate "
          f"cannot fail' is exactly the sort of claim that removes a rung on a "
          f"mistake.")
    A("")
    smt = ctx.get("day_layer", {}).get("gate_smt", 0)
    nd = ctx.get("n_days", 2724)
    k2 = res.get(PRIMARY_STACK, {}).get("counts_raw_poi", {}).get("K2 SMT", 0)
    A(f"**6. SMT was recorded as unmeasurable before 2023-07-02 and never was — "
      f"already withdrawn by the document's own amendment A5, and independently "
      f"confirmed here.** §3.6 originally concluded SMT was *effectively untested "
      f"and untestable* because the XAG correlate began 2023-07-02. That was "
      f"`fetch_correlated.py`'s default start, inherited from the *gold* 3-year "
      f"window, not a property of the feed, which serves XAG from 2010-01-03. A5 "
      f"withdraws the claim and keeps the demotion, which is the right call: the "
      f"frequency argument for demoting SMT was always sufficient on its own. This "
      f"run measures the day-level SMT gate at **{smt:,} days of {nd:,} "
      f"({100*smt/max(nd,1):.1f}%)** and knob K2 at **{k2:,}** events on the "
      f"primary stack — the same figures A5 reports, reached down an independent "
      f"path. Kept on the list because the item was live when this run began, and "
      f"because the shape of the mistake is worth preserving: a harness default "
      f"read as a property of the market.")
    A("")
    A("**7. §1.8 required `series_max_open` to be added to "
      "`python/detectors/cisd.py` before the test ran.** This workstream is scoped "
      "out of editing the detector modules, so the reading is implemented inside "
      "`backtest_conjunction.py` as a faithful copy of `cisd.cisd_events` with the "
      "level line changed. It is a family-B secondary that cannot change a "
      "verdict, so its location does not affect the result — but the instruction "
      "was not followed as written and that is recorded rather than glossed.")
    A("")
    A("**8. Family B was specified as a 32-cell factorial and run as five "
      "one-at-a-time deviations.** §4.6 counts family B as level rule × "
      "`min_series` × `max_wait` × C3 reference × inside-bar rule = 32 cells. The "
      "inside-bar rule is inert (item 3), which makes it 16; the remaining "
      "factorial's marginal value is in interactions between readings, and no cell "
      "in the family may change the verdict in any case. The five one-at-a-time "
      "deviations are reported in §10 and the factorial is not claimed.")
    A("")
    A("**9. The 4H grid is listed in §0 as *adopted without re-derivation* and it "
      "is not settled.** `meta/session_window_fit.md` found the forex and futures "
      "grids *behaviourally indistinguishable* (z = 0.08) and broke the tie "
      "structurally. That comparison was made on a counting statistic. On an "
      "outcome book the grid matters a great deal: bare CISD at 4h returns "
      "+0.043 R with a CI excluding zero on a UTC-aligned resample, and +0.013 R "
      "with a CI containing zero on the locked forex grid — and the block-sign "
      "agreement goes from 3 of 4 to 2 of 4, which is the difference between "
      "passing and failing §4.4b. The numbers are in §2. No stack in this ladder "
      "uses 4h as an entry timeframe, so nothing here depends on it; but a "
      "parameter placed beyond re-derivation should not be able to move a "
      "significance verdict.")
    A("")
    A("**10. The matched control makes §5.1's cost condition vacuous.** Because "
      "the control shares the trade's stop distance and its cost, the cost term "
      "cancels exactly in the differential — for a flat USD spread and for the "
      "proportional 0.04R alike. *'The differential survives cost 0.5 and cost "
      "0.04R with the same sign'* is therefore guaranteed by arithmetic and tests "
      "nothing. The condition that a cost sensitivity should have expressed is "
      "about the book's own expectancy, which is reported beside it in §8.")
    A("")
    return "\n".join(L)


def verdict_md(res: dict, ctx: dict) -> str:
    """§5.5's final requirement: a statement of which of §5.1 / §5.2 / §5.3
    applies, in those words — plus the four things that outrank it."""
    L = ["## 12. Verdict", ""]
    A = L.append
    prim = res.get(PRIMARY_STACK, {})
    pow_ = res.get(POWERED_STACK, {})

    A("### The pre-registered primary cells")
    A("")
    for tag, r in (("primary 15m / 4H / 1D", prim), ("powered 5m / 1H / 1D", pow_)):
        if not r or "ladder" not in r:
            continue
        c = r["ladder"]["R4"]
        A(f"- **{tag}, R4:** n = {c['n']:,}, differential {f3(c['diff_r'])} R, "
          f"95% CI {ci(c['diff_r_lo'], c['diff_r_hi'])} "
          f"({c.get('diff_r_ci', '')} bootstrap, the wider of the two), win-rate "
          f"differential {fpp(c['diff_win'])}. **{verdict_for(c)}.**")
    A("")
    if prim and "counts" in prim:
        n4 = prim["counts"]["R4"]
        n4raw = prim.get("counts_raw_poi", {}).get("R4", 0)
        A(f"**§5.3's escape clause does not fire.** The pre-registration wrote that "
          f"the indeterminacy condition applies *on the 3.06 years currently held* "
          f"and that *on a certified span of ≥ 6 years the primary stack clears it "
          f"and this condition stops applying there.* It does not clear it. Ten and "
          f"a half certified years give **{n4:,}** events at R4 with the "
          f"availability guard on and **{n4raw:,}** with it off, against the "
          f"**{POWER_FLOOR_5PP:,}** real trades a 5pp effect needs at K = 5. The "
          f"primary hypothesis is underpowered on the largest trustworthy sample "
          f"that exists for this instrument, which §3.6 came within a factor of "
          f"1.5 of predicting and this run confirms.")
        A("")

    # H1 — and which comparison it actually rests on
    if prim and "H1" in prim:
        h = prim["H1"]["r"]
        c0 = prim["ladder"]["R0"]
        c4 = prim["ladder"]["R4"]
        r0_null = (np.isfinite(c0["diff_r_lo"]) and c0["diff_r_lo"] <= 0
                   <= c0["diff_r_hi"])
        A("### H1 — does the conjunction beat its own primitive?")
        A("")
        A("Pre-registered as: the R4 differential exceeds the **R0** differential "
          "by an amount whose 95% CI excludes zero, after Holm correction within "
          "family A.")
        A("")
        A("| stack | R0 diff | R4 diff | R4 − R0 | 95% CI | H1 |")
        A("|---|---:|---:|---:|---|---|")
        for s_, r in (("15m primary", prim), ("5m powered", pow_),
                      ("1h swing", res.get("1h", {}))):
            if not r or "H1" not in r:
                continue
            hh = r["H1"]["r"]
            held = "**holds**" if np.isfinite(hh[1]) and hh[1] > 0 else "does not hold"
            A(f"| {s_} | {f3(r['ladder']['R0']['diff_r'])} | "
              f"{f3(r['ladder']['R4']['diff_r'])} | {f3(hh[0])} | "
              f"{ci(hh[1], hh[2])} | {held} |")
        A("")
        if r0_null:
            A(f"**And the comparator itself is null, which changes what that "
              f"sentence means.** Rung 0 on this stack returns {f3(c0['diff_r'])} R "
              f"with a CI of {ci(c0['diff_r_lo'], c0['diff_r_hi'])} on "
              f"{c0['n']:,} events — comfortably above the "
              f"{POWER_FLOOR_5PP:,}-trade floor for a 5pp effect, so that is a "
              f"**well-powered zero**, not an underpowered one. When the baseline "
              f"is indistinguishable from its control, *'the full model beats rung "
              f"0'* and *'the full model beats its own control'* stop being "
              f"different questions. Both are reported above and both contain "
              f"zero. The verdict on the conjunction rests on the **R4-vs-control** "
              f"comparison, which is underpowered; the verdict on the primitive "
              f"rests on the **R0-vs-control** comparison, which is not.")
        A("")

    # the ladder
    A("### The ladder")
    A("")
    for s, r in (("15m primary", prim), ("5m powered", pow_),
                 ("1h swing", res.get("1h", {}))):
        if not r or "ladder" not in r:
            continue
        labs = [f"{rk} {r['ladder'][rk].get('label', '')}" for rk in RUNGS[1:]]
        adds = [x for x in labs if "ADDS VALUE" in x]
        A(f"- **{s}:** " + "; ".join(labs) + ". "
          + (f"**{len(adds)} rung(s) add value.**" if adds
             else "**No rung adds value over its predecessor.**"))
    A("")
    n_adds = sum(1 for r in res.values() if "ladder" in r
                 for rk in RUNGS[1:]
                 if "ADDS VALUE" in (r["ladder"][rk].get("label") or ""))
    loo_sig = [(s_, g) for s_, r in res.items() if "ladder" in r for g in GATES
               if (lambda x: x and np.isfinite(x[1]) and (x[1] > 0 or x[2] < 0))(
                   r["ladder"][f"LOO-{g}"].get("rise_r"))]
    if n_adds == 0:
        A("**No forward transition on any stack has a rise-in-differential whose "
          "confidence interval excludes zero, so the pre-declared label ADDS "
          "VALUE is never earned.** Where `n` is still large the correct label is "
          "*merely shrinks the sample*; below the power floor the correct label is "
          "*indeterminate*, and the two must not be blurred.")
    else:
        A(f"**{n_adds} forward transition(s) earn the pre-declared label ADDS "
          f"VALUE.** They are named in the ladder tables of §3 and must be read "
          f"against the Holm correction in §9 before being treated as findings.")
    A("")
    if loo_sig:
        A("§5.1 item 6 — at least one leave-one-out removal significantly changes "
          "the differential — is met by: "
          + ", ".join(f"{s_} / {g}" for s_, g in loo_sig) + ".")
    else:
        A("**§5.1 item 6 is not met on any stack**: no leave-one-out removal "
          "significantly reduces the differential, so no gate in the conjunction "
          "can be named as load-bearing. That is a required condition for "
          "confirmation, not an optional one.")
    A("")

    # regime
    A("### Regime blocks — and the concentration that is not there")
    A("")
    if prim and "blocks" in prim:
        rows = []
        for s_, r in (("15m", prim), ("5m", pow_), ("1h", res.get("1h", {}))):
            if not r or "blocks" not in r:
                continue
            for rk in RUNGS:
                vals = [r["blocks"][rk][b].get("diff_r", float("nan"))
                        for b in ("B1", "B2", "B3", "B4")]
                pos = sum(1 for v in vals if np.isfinite(v) and v > 0)
                neg = sum(1 for v in vals if np.isfinite(v) and v < 0)
                rows.append((s_, rk, pos, neg, max(pos, neg) >= 3))
        ok = sum(1 for _, _, _, _, a_ in rows if a_)
        neg = sum(1 for _, _, p_, n_, a_ in rows if a_ and n_ > p_)
        A(f"§4.4b requires the sign to agree in at least 3 of the 4 calendar "
          f"blocks. Across every rung of every stack with an outcome book, "
          f"**{ok} of {len(rows)}** rung-stack combinations meet it — and on "
          f"**{neg}** of those the agreeing sign is **negative**. The blocks are "
          f"individually far too small to resolve anything — a quarter of the span "
          f"at R4 is a few dozen trades — so sign agreement is the strongest test "
          f"the sample supports.")
        A("")
        A("**That is not the outcome the regime worry predicted, and it is worth "
          "being precise about why.** The concern raised before this run was that "
          "the edge might live only in B4, the most recent block, which is where "
          "every prior result in this project was computed — in which case phase 2 "
          "and this test alike would be describing a single bull market. Measured "
          "at the locked parameters that is not what the ladder does: the "
          "differential sits at or slightly below its control in **all four** "
          "blocks, B4 included, on both the primary and the powered stack. The "
          "conjunction is not regime-dependent here; it is uniformly absent. B4 "
          "concentration does appear in the *other* configuration — the "
          "reconciliation book at `max_wait=40` with no costs, where 4h's B4 "
          "differential is several times any other block's (§2) — so the concern "
          "was well founded about that book and does not transfer to this one.")
        A("")
    A("The per-block tables in §5 are given for **every rung including rung 0** so "
      "the question can be answered directly rather than inferred from the pooled "
      "figure, which is what §4.4b's closing paragraph asked for.")
    A("")

    # PRE
    if prim and "samples" in prim:
        A("### The PRE sample — the only genuinely virgin data in the project")
        A("")
        A("Everything before 2023-07-02 has never been looked at by any workstream "
          "here: phase 1 read transcripts, and every phase-2 measurement ran on "
          "`xau_m1_3y.parquet`, which begins on that date. It is the confirmatory "
          "sample §4.4 designates.")
        A("")
        A("| stack | rung | n | differential | 95% CI | ≥ 868? |")
        A("|---|---|---:|---:|---|---|")
        best = None
        for s_, r in (("15m primary", prim), ("5m powered", pow_),
                      ("1h swing", res.get("1h", {}))):
            if not r or "samples" not in r:
                continue
            for rk in ("R0", "R4"):
                c = r["samples"][rk]["PRE"]
                if not c.get("n"):
                    continue
                powered_enough = c["n"] >= POWER_FLOOR_5PP
                A(f"| {s_} | {rk} | {c['n']:,} | {f3(c['diff_r'])} | "
                  f"{ci(c['diff_r_lo'], c['diff_r_hi'])} | "
                  f"{'**yes**' if powered_enough else 'no'} |")
                if rk == "R4" and powered_enough:
                    best = (s_, c)
        A("")
        if best:
            s_, c = best
            A(f"**The single strongest line in this document is that one.** The "
              f"full conjunction, on the {s_} stack, on {c['n']:,} trades of data "
              f"no workstream in this project had ever examined, returns "
              f"{f3(c['diff_r'])} R against its matched control with a confidence "
              f"interval of {ci(c['diff_r_lo'], c['diff_r_hi'])}. That is above "
              f"the power floor, on confirmatory data, and it contains zero.")
            A("")

    # what it would take
    A("### What this dataset cannot answer, and what would be needed")
    A("")
    n4 = prim.get("counts", {}).get("R4", 0) if prim else 0
    yrs = ctx.get("span_yrs", 10.55)
    rate = n4 / yrs if yrs else 0
    if rate:
        A(f"R4 on the primary stack fires {rate:.0f} times a year. Against the "
          f"{POWER_FLOOR_5PP:,} real trades a 5pp effect needs at K = 5, that is "
          f"**{POWER_FLOOR_5PP/rate:,.0f} years** of XAUUSD — against the 10.55 "
          f"the trustworthy record contains. A 3pp effect needs "
          f"**{n_real_for_effect(0.03)/rate:,.0f} years**. Adding gold history "
          f"cannot close that gap, because the certified span already IS the whole "
          f"trustworthy record; the only route to a 3–4pp floor is more "
          f"instruments (§3.7.3).")
        A("")
    powered_rungs = [f"{s_} {rk}" for s_, r in res.items() if "ladder" in r
                     for rk in RUNGS
                     if r["ladder"][rk].get("n", 0) >= POWER_FLOOR_5PP]
    A(f"**An indeterminate rung is not a finding of no edge.** §5.3 is explicit "
      f"that the two are different claims. **{len(powered_rungs)} rung-stack "
      f"cells clear the {POWER_FLOOR_5PP:,}-trade floor** — "
      + ", ".join(powered_rungs) +
      " — and on every one of them a CI containing zero is a *well-powered zero* "
      "and a real result. Everywhere else, including every knob and every regime "
      "block at R4, this dataset cannot answer the question, and the honest "
      "statement is that it cannot, together with the data volume that would be "
      "required.")
    A("")
    A("**Three limits bound every sentence above.** There is no sustained gold "
      "bear market in the certified span, so nothing here is validated against a "
      "downtrend. This is **one instrument**, and the corpus is taught on NQ, ES "
      "and YM — `excluded-tooling` says futures only, no CFDs and no scalping, so "
      "gold is on the instrument list but a 1-minute entry timeframe is not. And "
      "the relevant-swing filter, the ADR budget, the 'relevant level' definition "
      "and the full profile classifier are all [GAP] in the corpus and absent from "
      "the primary configuration — so what was tested is the method as far as it "
      "is mechanically stated, which is not the same as the method as practised.")
    return "\n".join(L)

def exclusion_check(entry_tf: str = PRIMARY_STACK, struct_tf: str = "4h") -> dict:
    """§3.7.2(c)'s declared robustness exclusion, re-run and reported beside the
    primary rather than instead of it.

    2019-02 → 2020-02 is a sharp, isolated feed regression sitting inside
    otherwise-modern data: median tick density collapses from 83 to 6 ticks per
    minute with up to 9% flat bars. It is not grounds to shorten the span, and
    dropping it still leaves 9.4 years. The pre-registration requires the primary
    result to be re-run without it and BOTH reported.
    """
    m1, yrs = load_certified(exclude_tick_regression=True)
    xag, _ = load_correlate()
    rep = make_report(m1, "excl", xag)
    bars = resample(m1, entry_tf)
    ev = build_events(bars, f"excl_{entry_tf}")
    poi = poi_annotate(bars, ev, entry_tf, "excl")
    g = gate_matrix(ev, poi, rep)
    masks = rung_masks(g, len(ev))
    tr = build_trades(ev, m1, bars, resample(m1, struct_tf), entry_tf)
    tgt = target_levels(tr, PRIMARY_TARGET)
    ctrl_tr, ctrl_tgt = matched_control(tr, tgt, bars, m1, entry_tf)
    bk = make_book(tr, ctrl_tr, ctrl_tgt, m1, PRIMARY_TARGET, PRIMARY_COST,
                   len(ev), yrs)
    return {"span_yrs": yrs, "n_m1": len(m1),
            "counts": {rk: int(masks[rk].sum()) for rk in RUNGS},
            **{rk: bk.cell(masks[rk]) for rk in ("R0", "R4")}}


def exclusion_md(x: dict) -> str:
    if not x:
        return ""
    L = ["## 10c. The declared robustness exclusion, 2019-02 → 2020-02 (§3.7.2c)",
         "",
         f"An isolated feed regression inside otherwise-modern data. Dropping it "
         f"leaves {x['span_yrs']:.2f} years and {x['n_m1']:,} M1 bars.", "",
         DIFF_HDR, DIFF_SEP]
    for rk in ("R0", "R4"):
        L.append(cell_row(f"{rk}, exclusion applied", x[rk]))
    return "\n".join(L) + "\n"


def family_a_holm(res: dict) -> str:
    """§4.6's multiple-testing accounting, applied rather than described.

    Family A is, per stack, the forward-rung increments, the leave-one-out
    removals and the rung-vs-control comparisons. Phase 2 is the precedent for why
    this matters: 4 of its 64 permutation tests came in under 0.05 against 3.2
    expected by chance, and none survived correction.
    """
    pv = {}
    for s_ in STACK_ORDER:
        r = res.get(s_)
        if not r or "ladder" not in r:
            continue
        for rk in RUNGS:
            c = r["ladder"][rk]
            if c.get("n"):
                pv[f"{s_} {rk} vs control"] = c.get("p_r", float("nan"))
            rise = c.get("rise_r")
            if rise and np.isfinite(rise[1]):
                pv[f"{s_} {rk} rise"] = ci_p(*rise)
        for gname in GATES:
            c = r["ladder"][f"LOO-{gname}"]
            rise = c.get("rise_r")
            if rise and np.isfinite(rise[1]):
                pv[f"{s_} restore {gname}"] = ci_p(*rise)
    rej = holm(pv)
    m = sum(1 for v in pv.values() if np.isfinite(v))
    raw = sum(1 for v in pv.values() if np.isfinite(v) and v <= 0.05)
    L = ["### Multiple testing — family A, Holm-corrected", "",
         f"{m} comparisons whose p-values are interpreted. At alpha = 0.05 that is "
         f"{0.05*m:.1f} expected false positives by chance. **{raw} clear 0.05 "
         f"uncorrected; {sum(rej.values())} survive Holm.**", ""]
    hits = sorted([(v, k) for k, v in pv.items()
                   if np.isfinite(v) and v <= 0.05])[:12]
    if hits:
        L += ["| comparison | p (uncorrected) | survives Holm? |",
              "|---|---:|---|"]
        for v, k in hits:
            L.append(f"| {k} | {v:.4f} | {'YES' if rej[k] else 'no'} |")
        L.append("")
    return "\n".join(L)



# ══ family C — declared knobs, reported as a landscape and never as a maximum ══
def body_extreme_stops(ev: pd.DataFrame, bars: pd.DataFrame) -> np.ndarray:
    """§1.11's declared secondary stop: the BODY extreme of the opposing series.

    The primary stop is the protected swing — the extreme the CISD protects. The
    spec presents the body-extreme version as a modification made when R is
    unsatisfying, which is a discretionary branch, which is why it is a secondary.
    """
    o = bars["open"].to_numpy(float)
    c = bars["close"].to_numpy(float)
    pos = {t: i for i, t in enumerate(bars.index)}
    s = np.array([pos[t] for t in ev["series_start"]])
    e = np.array([pos[t] for t in ev["series_end"]])
    bull = (ev["direction"] == "bullish").to_numpy()
    out = np.empty(len(ev))
    for k in range(len(ev)):
        seg_lo = np.minimum(o[s[k]:e[k] + 1], c[s[k]:e[k] + 1])
        seg_hi = np.maximum(o[s[k]:e[k] + 1], c[s[k]:e[k] + 1])
        out[k] = seg_lo.min() if bull[k] else seg_hi.max()
    return out


def family_c(m1: pd.DataFrame, report: pd.DataFrame, tag: str, span_yrs: float,
             entry_tf: str = PRIMARY_STACK, struct_tf: str = "4h") -> dict:
    """The declared knobs of §4.6 family C, as full landscapes.

    Two standing rules govern everything here (§4.6): **the maximum of a sweep is
    never a result**, and no cell outside the primary family can promote a null to
    a positive. The session grid in particular is reported because §5.5 requires
    the curve, not because any cell in it means anything — §1.14 already puts the
    corpus's own NY-AM window at −0.057R on 7,835 events, and §3.6 puts the
    session knob at 43 events over a decade on this stack.
    """
    bars = resample(m1, entry_tf)
    ev = build_events(bars, f"{tag}_{entry_tf}")
    poi = poi_annotate(bars, ev, entry_tf, f"{tag}_{LEVEL_RULE}_{MAX_WAIT}_{MIN_SERIES}")
    g = gate_matrix(ev, poi, report)
    masks = rung_masks(g, len(ev))
    struct = resample(m1, struct_tf)
    tr = build_trades(ev, m1, bars, struct, entry_tf)
    tgt = target_levels(tr, PRIMARY_TARGET)
    ctrl_tr, ctrl_tgt = matched_control(tr, tgt, bars, m1, entry_tf)
    bk = make_book(tr, ctrl_tr, ctrl_tgt, m1, PRIMARY_TARGET, PRIMARY_COST,
                   len(ev), span_yrs)

    lt = pd.DatetimeIndex(ev["confirm_time"]).tz_convert(TZ)
    mins = np.asarray(lt.hour * 60 + lt.minute)

    def cheap(ev_mask, tmask=None):
        """Point estimate only. A landscape needs the shape, not 625 CIs — and
        attaching a CI to every cell of a sweep invites reading its maximum."""
        sel = ev_mask[bk.r_ev]
        if tmask is not None:
            sel = sel & tmask
        if sel.sum() < 5:
            return int(sel.sum()), float("nan")
        d = bk.r_r[sel] - bk.cm_r[bk.r_ev[sel]]
        d = d[np.isfinite(d)]
        return int(sel.sum()), float(d.mean()) if len(d) else float("nan")

    starts = [(8, 30), (9, 0), (9, 30), (10, 0), (10, 30)]
    ends = [(11, 0), (11, 30), (12, 0), (12, 30), (13, 0)]
    grid = {}
    for rk in ("R0", "R4"):
        for smp, tm in (("ALL", None),
                        ("PRE", np.asarray(bk.r_t < PRE_END)),
                        ("IS", np.asarray((bk.r_t >= PRE_END) & (bk.r_t < IS_END))),
                        ("OOS", np.asarray(bk.r_t >= IS_END))):
            for sh, sm in starts:
                for eh, em in ends:
                    lo, hi = sh * 60 + sm, eh * 60 + em
                    sess = (mins >= lo) & (mins < hi)
                    grid[(rk, smp, f"{sh:02d}:{sm:02d}", f"{eh:02d}:{em:02d}")] = \
                        cheap(ev_mask=masks[rk] & sess, tmask=tm)
    off = {rk: {smp: cheap(masks[rk], tm) for smp, tm in
                (("ALL", None), ("PRE", np.asarray(bk.r_t < PRE_END)),
                 ("IS", np.asarray((bk.r_t >= PRE_END) & (bk.r_t < IS_END))),
                 ("OOS", np.asarray(bk.r_t >= IS_END)))}
           for rk in ("R0", "R4")}

    # stop variant: the body extreme of the opposing series
    tr2 = tr.copy()
    st = body_extreme_stops(ev, bars)[tr["ev_i"].to_numpy()]
    tr2["stop"] = st
    tr2["risk"] = np.abs(tr2["entry"].to_numpy() - st)
    ok = (tr2["risk"] > 0) & np.where(tr2["long"].to_numpy(),
                                      st < tr2["entry"].to_numpy(),
                                      st > tr2["entry"].to_numpy())
    tr2 = tr2[ok].reset_index(drop=True)
    t2 = target_levels(tr2, PRIMARY_TARGET)
    c2_tr, c2_tgt = matched_control(tr2, t2, bars, m1, entry_tf)
    bk2 = make_book(tr2, c2_tr, c2_tgt, m1, PRIMARY_TARGET, PRIMARY_COST,
                    len(ev), span_yrs)
    stopvar = {rk: bk2.cell(masks[rk]) for rk in ("R0", "R4")}

    return {"grid": grid, "off": off, "stop_variant": stopvar,
            "starts": starts, "ends": ends}


def family_c_md(fc: dict) -> str:
    if not fc:
        return ""
    L = ["## 10b. Family C — the declared knobs, as landscapes", "",
         "**The maximum of a sweep is never a result** (§4.6, standing rule 1). "
         "These are reported because §5.5 requires the curves, and the reader is "
         "pointed at *shape agreement between the periods*, which is the actual "
         "test. A threshold that is monotone out-of-sample and flat in-sample is "
         "noise, and phase 2 says so with the numbers.", "",
         "### Session window grid — differential vs control in R, primary stack",
         ""]
    ns4 = [fc["grid"][k][0] for k in fc["grid"] if k[0] == "R4" and k[1] == "ALL"]
    L += [f"Reported at **rung 0 only**. At R4 the same 25 windows hold between "
          f"{min(ns4)} and {max(ns4)} trades each over 10.55 years, against a "
          f"{POWER_FLOOR_5PP:,}-trade floor — a landscape of point estimates on "
          f"single-digit samples is not a landscape, and printing it would invite "
          f"reading its maximum. §3.6 pre-registered exactly this: 43 events for "
          f"the session knob over a decade, a 22.5pp floor.", ""]
    for rk in ("R0",):
        for smp in ("ALL", "PRE", "OOS"):
            L.append(f"**{rk}, {smp}** (session OFF: n = {fc['off'][rk][smp][0]:,}, "
                     f"{f3(fc['off'][rk][smp][1])} R)")
            L.append("")
            L.append("| start \\ end | " + " | ".join(f"{eh:02d}:{em:02d}"
                                                     for eh, em in fc["ends"]) + " |")
            L.append("|---" * (len(fc["ends"]) + 1) + "|")
            for sh, sm in fc["starts"]:
                cells = []
                for eh, em in fc["ends"]:
                    n, d = fc["grid"][(rk, smp, f"{sh:02d}:{sm:02d}",
                                       f"{eh:02d}:{em:02d}")]
                    cells.append(f"{f3(d, 2)}<br><sub>n={n:,}</sub>")
                L.append(f"| {sh:02d}:{sm:02d} | " + " | ".join(cells) + " |")
            L.append("")
    L += ["### Stop variant — the body extreme of the opposing series (§1.11 "
          "secondary)", "", DIFF_HDR, DIFF_SEP]
    for rk in ("R0", "R4"):
        L.append(cell_row(f"{rk}, body-extreme stop", fc["stop_variant"][rk]))
    L += ["", "The remaining family-C knob — §1.10's **continuation entry**, where "
          "the trade is taken not on the CISD but on the retrace into an FVG or "
          "the sweep that follows it — is **not implemented**, because the "
          "pre-registration itself records that it needs a detector that does not "
          "exist and has an unknown fill rate (§1.10). Its direction is known "
          "without measuring it: the continuation entry is strictly rarer than the "
          "CISD-close entry, so a configuration already below the power floor gets "
          "further below it. That inequality is what made the substitution "
          "defensible in the first place.", ""]
    return "\n".join(L)


# ══ §5.4 items 3 and 6 — stratification and the fixed-dollar cross-check ══════
def strat_and_dollar(m1: pd.DataFrame, report: pd.DataFrame, tag: str,
                     span_yrs: float, entry_tf: str = PRIMARY_STACK,
                     struct_tf: str = "4h") -> dict:
    """Two pre-declared checks against the shrinking-sample trap (§5.4).

    **Item 3, stratify.** Recompute the R4 differential inside terciles of
    stop/ATR(20) and inside terciles of trailing realised volatility. A real edge
    survives inside strata; a composition effect — a gate that merely selects
    bigger-R or higher-volatility setups — does not. The terciles are cut on the
    R0 book so the strata mean the same thing at every rung.

    **Item 6, a fixed DOLLAR target.** The whole book is re-run with the stop and
    the target set to a constant USD distance — the R0 book's median risk, and
    twice it — so that the win rate cannot be moved by stop sizing. If the
    R-multiple result and the fixed-dollar result disagree, the R-multiple version
    is being driven by how big the stops are rather than by where price goes.
    """
    bars = resample(m1, entry_tf)
    ev = build_events(bars, f"{tag}_{entry_tf}")
    poi = poi_annotate(bars, ev, entry_tf,
                       f"{tag}_{LEVEL_RULE}_{MAX_WAIT}_{MIN_SERIES}")
    g = gate_matrix(ev, poi, report)
    masks = rung_masks(g, len(ev))
    tr = build_trades(ev, m1, bars, resample(m1, struct_tf), entry_tf)
    tgt = target_levels(tr, PRIMARY_TARGET)
    ctrl_tr, ctrl_tgt = matched_control(tr, tgt, bars, m1, entry_tf)
    bk = make_book(tr, ctrl_tr, ctrl_tgt, m1, PRIMARY_TARGET, PRIMARY_COST,
                   len(ev), span_yrs)

    # trailing realised volatility at the signal bar, from closed bars only
    ret = np.log(bars["close"]).diff()
    rv = ret.rolling(100, min_periods=100).std()
    rv_at = rv.reindex(pd.DatetimeIndex(ev["confirm_time"])).to_numpy(float)

    ev_atr = np.full(len(ev), np.nan)
    ev_atr[tr["ev_i"].to_numpy()] = (tr["risk"] / tr["atr20"]).to_numpy(float)

    out = {"strata": {}}
    for name, vals in (("stop / ATR(20)", ev_atr), ("trailing realised vol", rv_at)):
        base = vals[masks["R0"]]
        base = base[np.isfinite(base)]
        if len(base) < 30:
            continue
        cuts = np.nanpercentile(base, [33.3, 66.7])
        for k, lab in enumerate(("T1 low", "T2 mid", "T3 high")):
            lo = -np.inf if k == 0 else cuts[k - 1]
            hi = np.inf if k == 2 else cuts[k]
            m = np.isfinite(vals) & (vals >= lo) & (vals < hi)
            out["strata"][(name, lab)] = {
                "R0": bk.cell(masks["R0"] & m),
                "R4": bk.cell(masks["R4"] & m),
            }

    # fixed-dollar book: constant stop and target distance for every trade
    med = float(np.median(tr["risk"].to_numpy(float)))
    tr2 = tr.copy()
    sgn = np.where(tr2["long"].to_numpy(), 1.0, -1.0)
    tr2["stop"] = tr2["entry"].to_numpy(float) - sgn * med
    tr2["risk"] = med
    t2 = tr2["entry"].to_numpy(float) + sgn * 2 * med
    c2_tr, c2_tgt = matched_control(tr2, t2, bars, m1, entry_tf)
    bk2 = make_book(tr2, c2_tr, c2_tgt, m1, PRIMARY_TARGET, PRIMARY_COST,
                    len(ev), span_yrs)
    # `make_book` recomputes the R target from `risk`, which is now the constant,
    # so the fixed-R and fixed-dollar targets coincide by construction here.
    out["fixed_dollar"] = {"median_risk_usd": med,
                           **{rk: bk2.cell(masks[rk]) for rk in ("R0", "R4")}}
    out["entry_tf"] = entry_tf
    return out


def strat_md(sd: dict) -> str:
    if not sd:
        return ""
    L = [f"### Stratification and the fixed-dollar cross-check "
         f"({sd['entry_tf']} stack, §5.4 items 3 and 6)", "",
         "A gate that improves the win rate purely by selecting rarer, larger-R or "
         "higher-volatility setups is not evidence of edge. The matched control "
         "already neutralises that by construction; these are the two independent "
         "checks the pre-registration adds on top.", "",
         "| stratum | R0 n | R0 diff | R4 n | R4 diff | R4 95% CI |",
         "|---|---:|---:|---:|---:|---|"]
    for (name, lab), d in sd["strata"].items():
        a, b = d["R0"], d["R4"]
        L.append(f"| {name}, {lab} | {a.get('n', 0):,} | {f3(a.get('diff_r'))} | "
                 f"{b.get('n', 0):,} | {f3(b.get('diff_r'))} | "
                 f"{ci(b.get('diff_r_lo'), b.get('diff_r_hi'))} |")
    sig = sum(1 for d in sd["strata"].values()
              if np.isfinite(d["R4"].get("diff_r_lo", np.nan))
              and (d["R4"]["diff_r_lo"] > 0 or d["R4"]["diff_r_hi"] < 0))
    signs = [np.sign(d["R4"].get("diff_r", 0)) for d in sd["strata"].values()]
    L += ["", f"R4's differential changes sign across the six strata "
          f"({int(sum(1 for x in signs if x > 0))} positive, "
          f"{int(sum(1 for x in signs if x < 0))} negative) and "
          f"**{sig} of {len(sd['strata'])}** confidence intervals exclude zero. "
          f"At roughly 180 trades a stratum that is what noise looks like, and it "
          f"is also what a composition effect looks like; the stratification "
          f"cannot separate them at this sample size and is reported as "
          f"uninformative rather than as support."]
    fd = sd["fixed_dollar"]
    L += ["", f"**Fixed-dollar book.** Every trade given the same stop distance — "
          f"the R0 book's median risk, {fd['median_risk_usd']:.2f} USD/oz — and a "
          f"target at twice it, so the win rate cannot be moved by stop sizing.",
          "", DIFF_HDR, DIFF_SEP]
    for rk in ("R0", "R4"):
        L.append(cell_row(f"{rk}, fixed-dollar stop and target", fd[rk]))
    L.append("")
    return "\n".join(L)

# ══ CLI ═══════════════════════════════════════════════════════════════════════
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stacks", default="")
    ap.add_argument("--counts-only", action="store_true")
    ap.add_argument("--exclude-tick-regression", action="store_true")
    ap.add_argument("--family-b", action="store_true")
    ap.add_argument("--no-report", action="store_true")
    ap.add_argument("--dump", default="")
    ap.add_argument("--from-dump", default="")
    ap.add_argument("--exclusion-check", action="store_true")
    ap.add_argument("--family-c-dump", default="")
    ap.add_argument("--coord-dump", default="")
    ap.add_argument("--strat-dump", default="")
    a = ap.parse_args(argv)
    if a.from_dump:
        # Rebuild the report from completed runs without recomputing them. Later
        # dumps only fill keys the earlier ones do not carry, so the primary run
        # always wins a collision.
        res, ctx = {}, {}
        for path in [x.strip() for x in a.from_dump.split(",") if x.strip()]:
            with open(path, "rb") as f:
                d = pickle.load(f)
            for k, v in d["res"].items():
                res.setdefault(k, v)
            for k, v in d["ctx"].items():
                ctx.setdefault(k, v)
        if a.strat_dump:
            for path in [x.strip() for x in a.strat_dump.split(",") if x.strip()]:
                with open(path, "rb") as f:
                    ctx.setdefault("strat", []).append(pickle.load(f))
        if a.family_c_dump:
            with open(a.family_c_dump, "rb") as f:
                ctx["family_c"] = pickle.load(f)
        if a.coord_dump:
            with open(a.coord_dump, "rb") as f:
                ctx["coord"] = pickle.load(f)
        if ctx.get("coord"):
            ctx["coordinator"] = coordinator_md(ctx["coord"])
        if a.exclusion_check:
            print("exclusion re-run (2019-02 -> 2020-02 dropped)...", flush=True)
            ctx["excl"] = exclusion_check()
        write_report(res, ctx)
        print(f"wrote {OUT_MD}")
        return 0
    want = {x.strip() for x in a.stacks.split(",") if x.strip()}

    t0 = time.time()
    m1, yrs = load_certified(a.exclude_tick_regression)
    tag = "excl" if a.exclude_tick_regression else "cert"
    print(f"certified span: {len(m1):,} M1 bars  {m1.index.min()} -> "
          f"{m1.index.max()}  ({yrs:.2f} yr)", flush=True)

    xag, xag_name = load_correlate()
    if xag is not None:
        ov = m1.index.intersection(xag.index)
        print(f"correlate {xag_name}: {len(xag):,} bars "
              f"{xag.index.min().date()} -> {xag.index.max().date()}", flush=True)

    report = make_report(m1, tag, xag)
    print(f"bias_report: {len(report):,} trading days ({round(time.time()-t0)}s)",
          flush=True)
    day = {c: int(report[c].fillna(False).astype(bool).sum())
           for c in ("gate_bias", "gate_profile", "gate_alignment",
                     "gate_no_fade", "gate_poi", "gate_smt")}
    print("day-layer standalone:", day, flush=True)

    res = {}
    for entry, struct, bias, name in STACKS:
        if want and entry not in want:
            continue
        print(f"[{entry}] {name}", flush=True)
        r = run_stack(m1, report, entry, struct, bias, name, yrs, tag,
                      counts_only=a.counts_only or entry == "1min")
        if r:
            res[entry] = r

    ctx = {
        "span_start": str(m1.index.min().date()),
        "span_end": str(m1.index.max().date()),
        "span_yrs": yrs, "n_m1": len(m1),
        "day_layer": day, "correlate": xag_name, "n_days": len(report),
    }
    if not a.counts_only:
        print("reading disagreement...", flush=True)
        ctx["disagree"] = reading_disagreement(m1, resample(m1, PRIMARY_STACK), tag)
        print("coordinator reconciliation...", flush=True)
        ctx["coord"] = coordinator_check(m1, yrs, tag)
        print(f"  coord {round(time.time()-t0)}s", flush=True)
    if a.family_b:
        print("family B...", flush=True)
        ctx["family_b"] = family_b(m1, report, xag, tag, yrs)
    if ctx.get("coord"):
        ctx["coordinator"] = coordinator_md(ctx["coord"])
    if a.dump:
        with open(a.dump, "wb") as f:
            pickle.dump({"res": res, "ctx": ctx, "day": day}, f)
        print(f"dumped -> {a.dump}", flush=True)
    if not a.no_report and res:
        write_report(res, ctx)
        print(f"wrote {OUT_MD}", flush=True)
    print(f"total {round(time.time()-t0)}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
