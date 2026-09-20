"""Event-frequency and power estimates for the conjunction pre-registration.

This script does NOT backtest anything. It answers one question only:

    if the TTrades conjunction is assembled gate by gate, HOW MANY EVENTS
    SURVIVE at each rung, and what is the smallest win-rate difference a
    sample that size could detect?

It is written for `meta/conjunction_preregistration.md` and is deliberately
run BEFORE any outcome is measured, so the answer "this dataset cannot carry
the test" can be stated in advance rather than discovered afterwards.

THE LADDER RUNS ON THE EVENT LAYER, NOT THE DAY LAYER. Intersecting all the
daily gates leaves 9 qualifying days in three years (~3/year), which no amount
of history repairs. Instead the unit of analysis is a CISD event on the entry
timeframe, and the daily gates are joined onto it as context columns, honouring
each gate's own `*_available_at` so a day's verdict is never used before it
resolved. See `meta/conjunction_preregistration.md` §2.

Method for the detectability floor is copied from `backtest_c2_wick.mde` so the
numbers are directly comparable with phase 2's published floors.

Gate implementations are the REAL modules -- `detectors.bias.bias_report` and
`detectors.poi.poi_gate_events` -- not the proxies this file originally carried.

Offline. No network.

Usage:
    python estimate_conjunction_power.py                    # certified span
    python estimate_conjunction_power.py --span 3y          # legacy 3-year file
    python estimate_conjunction_power.py --stacks 15min
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bars import load_m1, resample                        # noqa: E402
from detectors.cisd import cisd_events                    # noqa: E402
from detectors.bias import bias_report                    # noqa: E402
from detectors.poi import poi_gate_events                 # noqa: E402

TZ = "America/New_York"
RD = Path(__file__).resolve().parents[2]

# ── spans ─────────────────────────────────────────────────────────────────────
# The trading calendar changed in Oct 2015 (NY hour 17 goes from ~2-3k bars/yr to
# exactly zero and stays there), so pre-2016 gold is a different instrument for
# any session-dependent rule. `meta/xau_history_audit.md` certifies 2016+.
SPANS = {
    "certified": (RD / "m3_scalper" / "xau_m1_full.parquet", "2016-01-01", None),
    "full":      (RD / "m3_scalper" / "xau_m1_full.parquet", None, None),
    "3y":        (RD / "m3_scalper" / "xau_m1_3y.parquet",   None, None),
}
# Declared robustness exclusion: an isolated feed regression inside modern data.
TICK_REGRESSION = ("2019-02-01", "2020-02-29")

STACKS = [
    ("1min",  "15min", "4h",  "scalping model"),
    ("5min",  "1h",    "1D",  "playbook"),
    ("15min", "4h",    "1D",  "favourite / A+"),
    ("1h",    "1D",    "1W",  "swing model"),
]

P_WIN_2R = 0.36
CTRL_REPS = 5
SESSION_START_MIN, SESSION_END_MIN = 10 * 60, 12 * 60   # 10:00-12:00 NY


# ── power arithmetic ──────────────────────────────────────────────────────────
def mde(n1: int, n2: int, p: float = P_WIN_2R) -> float:
    """Smallest win-rate difference two samples this size could detect."""
    if n1 < 2 or n2 < 2:
        return float("nan")
    z = 1.959964 + 0.8416212
    return float(z * np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)))


def n_for_effect(effect: float, p: float = P_WIN_2R) -> float:
    """Events when BOTH arms are real trades, split evenly (rung vs rung)."""
    z = 1.959964 + 0.8416212
    return float(4 * p * (1 - p) * (z / effect) ** 2)


def n_real_for_effect(effect: float, p: float = P_WIN_2R, reps: int = CTRL_REPS
                      ) -> float:
    """REAL trades needed against a `reps`:1 matched control.

    This is the number that sets a CALENDAR requirement. The control arm is
    resampled from history already held, so it costs no market data. Charging it
    to the calendar overstates the requirement by 4*reps/(reps+1) = 3.33x at
    reps=5. See the pre-registration's amendment A1.
    """
    z = 1.959964 + 0.8416212
    return float(p * (1 - p) * (1 + 1 / reps) * (z / effect) ** 2)


def n_real_for_effect_R(effect_r: float, sd: float = 1.44,
                        reps: int = CTRL_REPS) -> float:
    z = 1.959964 + 0.8416212
    return float((z * sd) ** 2 * (1 + 1 / reps) / effect_r ** 2)


def mde_vs_control(n: int, reps: int = CTRL_REPS, p: float = P_WIN_2R) -> float:
    return mde(n, n * reps, p)


# ── data ──────────────────────────────────────────────────────────────────────
def load_span(span: str) -> tuple[pd.DataFrame, float]:
    path, lo, hi = SPANS[span]
    m1 = load_m1(path)
    if lo:
        m1 = m1[m1.index >= pd.Timestamp(lo, tz="UTC")]
    if hi:
        m1 = m1[m1.index <= pd.Timestamp(hi, tz="UTC")]
    yrs = (m1.index.max() - m1.index.min()).days / 365.25
    return m1, yrs


def load_correlate() -> pd.DataFrame | None:
    """XAG H1, the SMT correlate. Prefers the DEEP series.

    `xag_h1.parquet` starts 2023-07-02 -- not because OANDA lacks the history,
    but because `fetch_correlated.py` defaulted its start to the *gold 3-year*
    window. That default was briefly mistaken for a data limit and written into
    this project as the finding "SMT is unmeasurable before 2023". It was never
    true: XAG_USD H1 is served from 2010-01-03, same as gold. Always prefer
    `xag_h1_full.parquet`, and never infer a data limit from a file's extent
    without checking the fetch parameters that produced it.
    """
    for name in ("xag_h1_full.parquet", "xag_h1.parquet"):
        p = RD / "m3_scalper" / name
        if p.exists():
            x = pd.read_parquet(p)
            if "time" in x.columns:
                x = x.set_index("time")
            x.index = pd.to_datetime(x.index, utc=True)
            x = x[["open", "high", "low", "close"]].astype("float64").sort_index()
            x.attrs["source"] = name
            return x
    return None


# ── joining daily context onto events, without lookahead ──────────────────────
def join_day_gates(events: pd.DataFrame, report: pd.DataFrame,
                   cols: list[str], avail_col: str = "day_gates_available_at",
                   max_stale_days: int = 1) -> pd.DataFrame:
    """Join each event to the PRECEDING trading day's verdict, lookahead-free.

    `bias_report` classifies day D using information that resolves at D's close,
    so D's verdict is a statement about a day already over. Spec §2.3 says to
    "anticipate the same direction on the NEXT candle", so an event on day D+1
    uses day D. Two guards, both of which caught real bugs:

      * availability -- the event must occur at or after the joined day's
        `*_available_at`, so a verdict is never used before it resolved;
      * staleness -- the joined day must be within `max_stale_days` trading days
        of the event's own day. Without this, an event inherits the last day that
        happened to have a resolved verdict, which on a sparse column can be
        weeks earlier and silently fabricates a gate pass.

    Returns boolean columns; a failed join is False, never NaN.
    """
    from detectors.bias import trading_day

    day_index = list(report.index)
    day_pos = {d: i for i, d in enumerate(day_index)}
    ev_day = trading_day(pd.DatetimeIndex(events["confirm_time"]))
    av = pd.to_datetime(report[avail_col], utc=True).to_numpy()
    conf = events["confirm_time"].to_numpy()

    src = np.full(len(events), -1, dtype=int)
    for k, d in enumerate(ev_day):
        i = day_pos.get(d)
        if i is None or i == 0:
            continue
        # walk back at most max_stale_days trading days for a resolved verdict
        for j in range(i - 1, max(-1, i - 1 - max_stale_days), -1):
            if pd.notna(av[j]) and av[j] <= conf[k]:
                src[k] = j
                break

    out = pd.DataFrame(index=events.index)
    for c in cols:
        vals = report[c].to_numpy()
        if vals.dtype == object:
            vals = pd.Series(vals).fillna(False).to_numpy()
        got = np.where(src >= 0, vals[np.clip(src, 0, len(vals) - 1)], False)
        out[c] = pd.Series(got, index=events.index).fillna(False).astype(bool)
    out["_src"] = src
    return out


def join_day_num(events: pd.DataFrame, report: pd.DataFrame, col: str,
                 src: np.ndarray) -> np.ndarray:
    """Numeric column pulled through an already-computed join index."""
    vals = report[col].to_numpy()
    return np.where(src >= 0, vals[np.clip(src, 0, len(vals) - 1)], 0)


def run_stack(m1: pd.DataFrame, report: pd.DataFrame, entry_tf: str,
              struct_tf: str, bias_tf: str, name: str, span_yrs: float,
              max_wait: int = 3, min_series: int = 1) -> dict:
    t0 = time.time()
    e = resample(m1, entry_tf)

    ev = cisd_events(e, level_rule="series_open", left=2, right=2,
                     max_wait=max_wait, min_series=min_series)
    n0 = len(ev)
    if n0 == 0:
        return {}

    # --- gate: POI, at the EVENT layer where it actually bites ---------------
    # At the day layer POI removes zero days -- a full day of hourly bars almost
    # always contains an FVG or a sweepable swing -- which is a resolution
    # artefact, not a weak gate.
    ann = poi_gate_events(e, ev, timeframe=entry_tf, setup_type="reversal")
    poi = ann["poi_passed"].fillna(False).to_numpy().astype(bool)

    # --- daily gates as joined context columns -------------------------------
    cols = ["gate_bias", "gate_profile", "gate_alignment"]
    has_smt = ("gate_smt" in report.columns
               and report["gate_smt"].fillna(False).astype(bool).any())
    if has_smt:
        cols.append("gate_smt")
    dg = join_day_gates(ev, report, cols)
    src = dg["_src"].to_numpy()

    sign = np.where((ev["direction"] == "bullish").to_numpy(), 1, -1)
    # Direction agreement is part of the bias gate: a confirmed bias that points
    # the other way is not a pass.
    bdir = join_day_num(ev, report, "bias_dir_num", src)
    bias_g = dg["gate_bias"].to_numpy() & (bdir == sign)
    prof_g = dg["gate_profile"].to_numpy()
    algn_g = dg["gate_alignment"].to_numpy()
    smt_g = dg["gate_smt"].to_numpy() if has_smt else None

    lt = ev["confirm_time"].dt.tz_convert(TZ)
    tt = (lt.dt.hour * 60 + lt.dt.minute).to_numpy()
    sess = (tt >= SESSION_START_MIN) & (tt < SESSION_END_MIN)

    gates = {"poi": poi, "bias": bias_g, "profile": prof_g, "align": algn_g}
    order = ["poi", "bias", "profile", "align"]
    labels = {"poi": "R1 + POI (event layer)", "bias": "R2 + HTF bias",
              "profile": "R3 + profile support", "align": "R4 + TF alignment"}

    rungs = [("R0 bare CISD", np.ones(n0, bool))]
    cum = np.ones(n0, bool)
    for g in order:
        cum = cum & gates[g]
        rungs.append((labels[g], cum.copy()))
    full = cum.copy()
    rungs.append(("K1 + session (knob)", full & sess))
    if smt_g is not None:
        rungs.append(("K2 + SMT (knob)", full & smt_g))
        rungs.append(("K3 + session + SMT", full & sess & smt_g))

    loo = {}
    for g in order:
        m = np.ones(n0, bool)
        for h in order:
            if h != g:
                m = m & gates[h]
        loo[g] = int(m.sum())

    solo = {g: int(v.sum()) for g, v in gates.items()}
    solo["session"] = int(sess.sum())
    if smt_g is not None:
        solo["smt"] = int(smt_g.sum())

    return {
        "name": name, "entry_tf": entry_tf, "struct_tf": struct_tf,
        "bias_tf": bias_tf, "entry_bars": len(e), "span_yrs": span_yrs,
        "rungs": [(lab, int(m.sum())) for lab, m in rungs],
        "solo": solo, "loo": loo, "full": int(full.sum()),
        "secs": round(time.time() - t0, 1),
    }


def fmt(res: dict) -> str:
    L = [f"\n### {res['name']}  —  entry {res['entry_tf']} / structure "
         f"{res['struct_tf']} / bias {res['bias_tf']}  "
         f"({res['entry_bars']:,} entry bars, {res['secs']}s)", "",
         "| rung | events | per yr | vs R0 | MDE vs prior | MDE vs 5x ctrl | "
         "yrs to 5pp | yrs to 3pp |",
         "|---|---:|---:|---:|---:|---:|---:|---:|"]
    prev = None
    n0 = res["rungs"][0][1]
    span = res["span_yrs"]
    for lab, n in res["rungs"]:
        vs = mde(n, prev) if prev and not lab.startswith("K") else float("nan")
        per_yr = n / span
        y5 = n_real_for_effect(0.05) / per_yr if per_yr else float("nan")
        y3 = n_real_for_effect(0.03) / per_yr if per_yr else float("nan")
        L.append(f"| {lab} | {n:,} | {per_yr:,.0f} | {100.0*n/n0:.1f}% | "
                 f"{'' if np.isnan(vs) else f'{100*vs:.1f}pp'} | "
                 f"{100*mde_vs_control(n):.1f}pp | {y5:,.1f} | {y3:,.1f} |")
        if not lab.startswith("K"):
            prev = n
    L += ["", "Each gate alone: " + ", ".join(
        f"{k} {v:,} ({100.0*v/n0:.0f}%)" for k, v in res["solo"].items()), "",
        "| leave-one-out (full model minus) | events | vs full |",
        "|---|---:|---:|"]
    for g, v in res["loo"].items():
        L.append(f"| {g} | {v:,} | x{v/max(res['full'],1):.2f} |")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--span", default="certified", choices=list(SPANS))
    ap.add_argument("--stacks", default="")
    ap.add_argument("--max-wait", type=int, default=3)
    ap.add_argument("--min-series", type=int, default=1)
    ap.add_argument("--cisd-scope", default="range", choices=("range", "wick"))
    ap.add_argument("--exclude-tick-regression", action="store_true")
    a = ap.parse_args(argv)
    want = {x.strip() for x in a.stacks.split(",") if x.strip()}

    m1, span_yrs = load_span(a.span)
    if a.exclude_tick_regression:
        lo, hi = (pd.Timestamp(t, tz="UTC") for t in TICK_REGRESSION)
        keep = (m1.index < lo) | (m1.index > hi)
        m1 = m1[keep]
        span_yrs -= (hi - lo).days / 365.25
    print(f"span={a.span}  M1 bars {len(m1):,}  "
          f"{m1.index.min()} -> {m1.index.max()}  ({span_yrs:.2f} yr)")
    print(f"CISD max_wait={a.max_wait} min_series={a.min_series} "
          f"cisd_scope={a.cisd_scope}")

    print(f"\nFloors (p={P_WIN_2R}, control {CTRL_REPS}:1):")
    for e in (0.03, 0.04, 0.05):
        print(f"  {100*e:4.0f}pp | real trades {n_real_for_effect(e):>9,.0f} "
              f"| both-arms-real {n_for_effect(e):>9,.0f}")
    for e in (0.03, 0.04, 0.05):
        assert abs(n_real_for_effect(e) - n_real_for_effect_R(3 * e)) \
            / n_real_for_effect(e) < 0.01, "power cross-check failed"
    print("  cross-check OK: Xpp and 3X-in-R floors agree")

    xag = load_correlate()
    if xag is not None:
        ov = m1.index.intersection(xag.index)
        print(f"correlate {xag.attrs.get('source','?')}: {len(xag):,} bars {xag.index.min().date()} -> "
              f"{xag.index.max().date()}")
        if xag.index.min() > m1.index.min():
            print(f"  !! correlate starts {xag.index.min().date()}, span starts "
                  f"{m1.index.min().date()} -- SMT measurable on the overlap only")

    t0 = time.time()
    report = bias_report(m1, correlate_h1=xag, cisd_scope=a.cisd_scope)
    report["bias_dir_num"] = report["bias"].map(
        {"bullish": 1, "bearish": -1}).fillna(0).astype(int)
    report["day_gates_available_at"] = report[
        ["bias_available_at", "profile_available_at", "alignment_available_at"]
    ].max(axis=1)
    print(f"\nbias_report: {len(report):,} trading days "
          f"({round(time.time()-t0,1)}s)")

    g = ["gate_bias", "gate_profile", "gate_alignment", "gate_no_fade",
         "gate_poi", "gate_smt"]
    cum = pd.Series(True, index=report.index)
    print(f"\nDAY-LAYER cascade (for reference only -- NOT the ladder):")
    print(f"  {'all days':26} {len(report):6,} 100.0%")
    for c in g:
        cum = cum & report[c].fillna(False).astype(bool)
        print(f"  + {c:24} {int(cum.sum()):6,} {100*cum.mean():5.1f}%")
    print("  standalone: " + ", ".join(
        f"{c.replace('gate_','')} {100*report[c].fillna(False).astype(bool).mean():.1f}%"
        for c in g))

    results = []
    for entry, struct, bias, name in STACKS:
        if want and entry not in want:
            continue
        r = run_stack(m1, report, entry, struct, bias, name, span_yrs,
                      max_wait=a.max_wait, min_series=a.min_series)
        if r:
            results.append(r)
            print(fmt(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
