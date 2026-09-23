"""No-lookahead enforcement, usable by every test type.

Two layers, because the project has been burned both ways (vault traps 3, 7, 9):

1. `assert_no_lookahead(decision_time, available_at)` — a hard inequality,
   checked for EVERY row: the decision may not precede the moment its inputs
   existed. Every test entry point calls it. `available_at` is the latest
   `close_time` of every bar (and `available_at` of every level) the concept's
   rule consumed; you compute it, the harness refuses to trust it silently.
   NaN/NaT in either column is an error — "never evaluated" must not look like
   "passed".

2. `probe_lookahead(detect_fn, events)` — the stronger, behavioural check, and
   (rules-2) a SYMMETRIC one. It re-runs YOUR detector on M1 cut at a time T and
   requires the set of events with decision_time in (T - recent, T] to be
   IDENTICAL, both ways and on every column, to the scored `events` in that
   window. Survival alone is not enough: a future condition used as a FILTER
   (the in-progress 4h bar must close up) is looser on cut data, so every surviving
   event still appears — only the EXTRA events on the cut data reveal it. A
   future-derived price (a stop at the next bars' low) comes out different or NaN
   on the cut data. Cuts are taken at sampled decision times AND at random times.
   The probe records the fingerprint of the `events` frame it checked; write_result
   refuses a result whose input frame is not that frame.

The phase-3 CISD-specific checker (`backtest_conjunction.assert_no_lookahead`,
per-gate for the ladder) remains the one to use for that ladder; these two are the
generic equivalents for the campaign.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

# columns the harness consumes; a probe may never be told to ignore them
HARNESS_COLS = ("decision_time", "available_at", "direction", "stop_px", "stop_dist",
                "target_px", "rr", "target_dist", "max_hold")


class LookaheadError(AssertionError):
    """A decision used information that did not exist yet. The run is invalid."""


def _utc(x, name: str) -> pd.DatetimeIndex:
    try:
        idx = pd.DatetimeIndex(x)
    except Exception as e:                       # noqa: BLE001
        raise LookaheadError(f"{name}: not datetimes ({e})") from None
    if idx.tz is None:
        raise LookaheadError(f"{name}: timestamps must be tz-aware (UTC)")
    return idx.tz_convert("UTC").as_unit("ns")


def assert_no_lookahead(decision_time, available_at, what: str = "events",
                        entry_time=None) -> dict:
    """Raise LookaheadError unless available_at <= decision_time (<= entry_time)
    for every row. Returns the check summary that goes into the result JSON."""
    d = _utc(decision_time, "decision_time")
    a = _utc(available_at, "available_at")
    if len(d) != len(a):
        raise LookaheadError(f"{what}: decision_time and available_at lengths differ")
    if pd.isna(d).any():
        raise LookaheadError(f"{what}: {int(pd.isna(d).sum())} NaT decision_time rows")
    if pd.isna(a).any():
        raise LookaheadError(
            f"{what}: {int(pd.isna(a).sum())} NaT available_at rows — a gate/level that "
            f"was never evaluated must be dropped or decided explicitly, not passed")
    bad = np.asarray(a > d)
    if bad.any():
        k = int(np.flatnonzero(bad)[0])
        raise LookaheadError(
            f"{what}: {int(bad.sum())} rows decide before their inputs exist; first: "
            f"decision {d[k]} < available_at {a[k]} (by {a[k] - d[k]})")
    out = {"rows_checked": int(len(d)),
           "min_slack_min": float(((d - a).total_seconds() / 60).min()) if len(d) else None}
    if entry_time is not None:
        e = _utc(entry_time, "entry_time")
        bad = np.asarray(e < d)
        if bad.any():
            k = int(np.flatnonzero(bad)[0])
            raise LookaheadError(f"{what}: entry {e[k]} before decision {d[k]}")
        out["entry_min_delay_min"] = float(((e - d).total_seconds() / 60).min()) if len(e) else None
    out["passed"] = True
    return out


def frame_fingerprint(df: pd.DataFrame) -> str:
    """Order-independent content hash of an events frame (columns + rows).

    Datetime columns are normalised to UTC nanoseconds, so the same instants in a
    different zone hash alike; row order does not matter."""
    if df is None:
        return "none"
    d = pd.DataFrame(df).reset_index(drop=True)
    cols = sorted(map(str, d.columns))
    d.columns = list(map(str, d.columns))
    d = d[cols]
    norm = {}
    for c in cols:
        x = d[c]
        if isinstance(x.dtype, pd.DatetimeTZDtype):
            x = pd.Series(x.dt.tz_convert("UTC").dt.tz_localize(None).astype("int64"))
        elif x.dtype.kind == "m":
            x = pd.Series(x.astype("int64"))
        elif x.dtype == object:
            x = x.map(lambda v: repr(v))
        norm[c] = x.to_numpy()
    nd = pd.DataFrame(norm, columns=cols)
    h = hashlib.sha1("|".join(cols).encode() + str(len(nd)).encode())
    if len(nd):
        try:
            rows = pd.util.hash_pandas_object(nd, index=False).to_numpy()
        except TypeError:
            rows = pd.util.hash_pandas_object(nd.astype(str), index=False).to_numpy()
        h.update(np.sort(rows).tobytes())
    return h.hexdigest()[:16]


def _canon(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    out = {}
    for c in cols:
        x = df[c]
        if isinstance(x.dtype, pd.DatetimeTZDtype) or x.dtype.kind == "M":
            try:
                x = pd.DatetimeIndex(x)
                if x.tz is None:
                    x = x.tz_localize("UTC")
                out[c] = x.tz_convert("UTC").tz_localize(None).as_unit("ns").to_numpy()
                continue
            except Exception:                            # noqa: BLE001
                pass
        if x.dtype.kind == "m":
            out[c] = pd.to_timedelta(x).to_numpy().astype("timedelta64[ns]")
        elif x.dtype.kind in "iufb":
            out[c] = x.to_numpy(float)
        else:
            try:
                out[c] = pd.to_datetime(x, utc=True).dt.tz_localize(None).to_numpy() \
                    if c in ("decision_time", "available_at") else x.astype(str).to_numpy()
            except Exception:                            # noqa: BLE001
                out[c] = x.astype(str).to_numpy()
    return pd.DataFrame(out)


def _diff_sets(a: pd.DataFrame, b: pd.DataFrame, cols: list, atol: float,
               rtol: float) -> str | None:
    """None if the two event sets are equal (multiset, per column, NaN == NaN)."""
    if len(a) != len(b):
        ta = sorted(map(str, a["decision_time"].tolist()))
        tb = sorted(map(str, b["decision_time"].tolist()))
        extra = sorted(set(ta) - set(tb))[:2]
        miss = sorted(set(tb) - set(ta))[:2]
        return (f"{len(a)} events on cut data vs {len(b)} in the scored book "
                f"(only on cut: {extra}; only in book: {miss})")
    if len(a) == 0:
        return None
    fcols = [c for c in cols if a[c].dtype.kind == "f"]
    order_cols = [c for c in cols if c not in fcols]
    ra = a.copy()
    rb = b.copy()
    for c in fcols:                                   # rounded sort keys only
        ra["_k" + c] = np.round(ra[c].to_numpy(float), 4)
        rb["_k" + c] = np.round(rb[c].to_numpy(float), 4)
    keys = order_cols + ["_k" + c for c in fcols]
    ra = ra.sort_values(keys, kind="stable", na_position="last").reset_index(drop=True)
    rb = rb.sort_values(keys, kind="stable", na_position="last").reset_index(drop=True)
    for c in order_cols:
        va, vb = ra[c].to_numpy(), rb[c].to_numpy()
        eq = (va == vb) | (pd.isna(va) & pd.isna(vb))
        if not np.asarray(eq).all():
            k = int(np.flatnonzero(~np.asarray(eq))[0])
            return f"column {c!r} differs at {ra['decision_time'][k]}: cut {va[k]} vs book {vb[k]}"
    for c in fcols:
        va, vb = ra[c].to_numpy(float), rb[c].to_numpy(float)
        both_nan = np.isnan(va) & np.isnan(vb)
        eq = both_nan | np.isclose(va, vb, atol=atol, rtol=rtol)
        if not eq.all():
            k = int(np.flatnonzero(~eq)[0])
            return (f"column {c!r} differs at {ra['decision_time'][k]}: cut {va[k]} vs "
                    f"book {vb[k]}")
    return None


def probe_lookahead(detect_fn, events: pd.DataFrame, m1: pd.DataFrame | None = None,
                    n_sample: int = 20, n_cuts: int = 200, lookback: str = "45D",
                    recent: str = "1D", ignore_cols=(), atol: float = 1e-6,
                    rtol: float = 1e-9, seed: int = 0, raise_on_fail: bool = True,
                    key_cols=None, compare_cols=None) -> dict:
    """Symmetric behavioural lookahead test (rules-2).

    detect_fn(m1_slice) -> DataFrame with a `decision_time` column and EVERY column
    of `events` (the frame you score — including any gate/mask column). It must
    build every bar series from the slice it is given (use
    `concept_lab.build_bars(m1_slice, tf)`), never from the cached full-span
    `bars()`, or the probe cannot see what it reads. Do all filtering INSIDE
    detect_fn: the probe compares its output with `events` as scored.

    For each cut time T — `n_sample` sampled decision times of `events` plus
    `n_cuts` random times inside the book's span [first event + lookback, last
    event] — the detector runs on M1 bars
    starting in [T - lookback, T) (every one closed by T), and the events it emits
    with decision_time in (T - recent, T] must EQUAL the scored events in that
    window: same count, same rows, every column (floats within atol/rtol, NaN only
    against NaN). An extra event on the cut data means a future FILTER; a missing
    or different one means a future input.

    `lookback` must exceed the detector's warm-up (swing lookbacks, ATRs, prior-week
    levels) by more than `recent`. `ignore_cols` may name derived diagnostic
    columns only; the harness-consumed columns can never be ignored.
    Returns a summary with the fingerprint of the checked `events` frame.
    `key_cols`/`compare_cols` are accepted for backward compatibility and ignored:
    every column is compared now.
    """
    from .data import load_m1
    bad_ign = [c for c in ignore_cols if c in HARNESS_COLS]
    if bad_ign:
        raise ValueError(f"cannot ignore harness-consumed columns {bad_ign}")
    m = load_m1() if m1 is None else m1
    ev = events.reset_index(drop=True)
    if "decision_time" not in ev.columns:
        raise ValueError("events need a decision_time column")
    cols = [c for c in map(str, ev.columns) if c not in ignore_cols]
    ev_c = _canon(ev, cols)
    dt = ev_c["decision_time"].to_numpy()
    lb, rc = pd.Timedelta(lookback), pd.Timedelta(recent)
    if rc >= lb:
        raise ValueError("recent must be shorter than lookback")
    t = pd.DatetimeIndex(m.index).tz_convert("UTC").tz_localize(None).as_unit("ns").to_numpy()
    rng = np.random.default_rng(seed)
    cuts = []
    if len(ev):
        pick = rng.choice(len(ev), size=min(n_sample, len(ev)), replace=False)
        cuts += [("targeted", dt[k]) for k in np.sort(pick)]
        lo_t, hi_t = dt.min() + lb, dt.max()        # stay inside the book's own span
    else:
        lo_t, hi_t = t[0] + lb, t[-1]
    cand = np.flatnonzero((t >= lo_t) & (t <= hi_t))
    if len(cand) and n_cuts:
        rnd = rng.choice(cand, size=min(n_cuts, len(cand)), replace=False)
        cuts += [("random", t[k] + np.timedelta64(1, "m")) for k in np.sort(rnd)]
    fails = []
    n_cmp = 0
    for kind, T in cuts:
        T = np.datetime64(T, "ns")
        lo = np.searchsorted(t, T - lb.to_timedelta64(), side="left")
        hi = np.searchsorted(t, T, side="left")               # bars starting < T
        got = detect_fn(m.iloc[lo:hi])
        if got is None:
            got = pd.DataFrame(columns=ev.columns)
        got = pd.DataFrame(got).reset_index(drop=True)
        miss = [c for c in cols if c not in got.columns]
        if miss and len(got):
            raise ValueError(f"detect_fn output lacks columns {miss} of the scored events; "
                             f"it must emit every column you score (or ignore_cols a "
                             f"derived, unscored column)")
        for c in miss:
            got[c] = pd.Series(dtype=ev[c].dtype)
        g_c = _canon(got, cols) if len(got) else ev_c.iloc[:0]
        gd = g_c["decision_time"].to_numpy() if len(got) else dt[:0]
        wg = (gd > T - rc.to_timedelta64()) & (gd <= T)
        we = (dt > T - rc.to_timedelta64()) & (dt <= T)
        n_cmp += int(we.sum())
        why = _diff_sets(g_c[wg].reset_index(drop=True), ev_c[we].reset_index(drop=True),
                         cols, atol, rtol)
        if why:
            fails.append((kind, str(pd.Timestamp(T, tz="UTC")), why))
    n_t = sum(1 for k, _ in cuts if k == "targeted")
    out = {"sampled": n_t, "n_targeted": n_t, "n_cuts": len(cuts) - n_t,
           "events_compared": n_cmp, "failures": len(fails), "examples": fails[:5],
           "columns": cols, "ignored": list(ignore_cols), "lookback": lookback,
           "recent": recent, "events_fp": frame_fingerprint(events), "symmetric": True,
           "passed": not fails}
    if fails and raise_on_fail:
        raise LookaheadError(
            f"probe_lookahead: {len(fails)}/{len(cuts)} cuts disagree with the scored "
            f"events — the detector reads the future (or its warm-up exceeds lookback-"
            f"recent={lb - rc}). First: {fails[0]}")
    return out
