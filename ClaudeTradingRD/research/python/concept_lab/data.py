"""Certified XAUUSD M1 and every bar series built from it, each bar carrying the
moment its information exists.

Settled conventions (do not relitigate — see the vault's *Session Timing on Gold*):
  * Timezone is America/New_York WITH DST. The daily candle rolls at 18:00 NY
    (`day_open_hour`, knob; 0 = midnight is the declared alternative).
  * The 4H grid is a KNOB (`grid4h`): "forex" 17/21/01/05/09/13 NY (default for
    gold), "futures" 18/22/02/06/10/14 NY, or "utc" (a plain UTC resample). The
    phase-3 outcome book moved from +0.047R to -0.0006R between grids, so the grid
    must be recorded in every operationalization that uses 4H.
  * Pre-2016 data is disqualified (Oct-2015 calendar break). `load_m1` returns
    the certified span only, via `backtest_conjunction.load_certified`.
  * Bars are LEFT-labelled: the index is the bar's START. `close_time` is the
    NOMINAL end of the bar in UTC — the first moment the bar's O/H/L/C are all
    known. A decision that uses a bar may be taken at `close_time` or later, never
    earlier; `asof()` enforces that for you. (Trap 3 and trap 9 of the vault's
    *Backtest Methodology Traps*.)

pandas here resolves datetimes in microseconds on resample; never do int64
arithmetic on timestamps — use Timedelta / searchsorted, as this module does.

Disk cache: resampled frames on the certified data are written to
`research/concept_campaign/.cache/` as parquet, via a temp file in the same
directory and `os.replace` (atomic on POSIX), so 30 concurrent agents can race to
build the same frame safely — the loser's rename just replaces an identical file.
"""
from __future__ import annotations

import hashlib
import inspect
import os
import re
import functools
import types
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_conjunction import (load_certified, PARQUET, CERTIFIED_START,  # noqa: F401
                                  TZ)
from detectors.bias import trading_day as _trading_day

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]                                  # .../research
CAMPAIGN_DIR = RESEARCH / "concept_campaign"
CACHE_DIR = Path(os.environ.get("CONCEPT_LAB_CACHE", CAMPAIGN_DIR / ".cache"))
RESULTS_DIR = Path(os.environ.get("CONCEPT_LAB_RESULTS", CAMPAIGN_DIR / "results"))

BARS_VERSION = "bars-1"
GRIDS_4H = {"forex": 1, "futures": 2, "utc": None}       # first NY grid hour mod 4
DEFAULT_GRID_4H = "forex"
DEFAULT_DAY_OPEN_HOUR = 18

_M1: pd.DataFrame | None = None
_MEM: dict = {}


def utc_ns(x) -> np.ndarray:
    """tz-aware times -> naive UTC datetime64[ns] ndarray (safe for searchsorted).

    pandas 3 returns an OBJECT array of Timestamps from a tz-aware
    `.to_numpy()`, and defaults naive conversions to microseconds; both break
    numpy comparisons silently or slowly. Always go through this.
    """
    idx = pd.DatetimeIndex(x)
    if idx.tz is None:
        raise ValueError("times must be tz-aware (UTC)")
    return idx.tz_convert("UTC").tz_localize(None).as_unit("ns").to_numpy()


def from_ns(a) -> pd.DatetimeIndex:
    """naive UTC datetime64 ndarray -> tz-aware UTC DatetimeIndex."""
    return pd.DatetimeIndex(np.asarray(a, dtype="datetime64[ns]")).tz_localize("UTC")


# ══ M1 ════════════════════════════════════════════════════════════════════════
def load_m1() -> pd.DataFrame:
    """Certified XAUUSD M1: UTC DatetimeIndex (bar START), float64 OHLC.

    2016-01-01 -> 2026-07-23, ~3.69M bars. Memoised per process; treat as
    read-only (do not mutate it — every other call shares the object).
    """
    global _M1
    if _M1 is None:
        m1, _ = load_certified()
        m1.index.name = "time"
        _M1 = m1
    return _M1


def is_certified(m1: pd.DataFrame | None) -> bool:
    return m1 is None or (_M1 is not None and m1 is _M1)


def data_signature() -> str:
    st = Path(PARQUET).stat()
    raw = f"{PARQUET}|{st.st_size}|{int(st.st_mtime)}|{CERTIFIED_START}|{BARS_VERSION}"
    return hashlib.sha1(raw.encode()).hexdigest()[:10]


def span(m1: pd.DataFrame | None = None) -> dict:
    m = load_m1() if m1 is None else m1
    a, b = m.index.min(), m.index.max()
    return {"start": str(a), "end": str(b), "years": round((b - a).days / 365.25, 3),
            "m1_bars": int(len(m))}


# ══ timeframes ════════════════════════════════════════════════════════════════
_ALIASES = {"m1": "1min", "m3": "3min", "m5": "5min", "m15": "15min", "m30": "30min",
            "h1": "1h", "h2": "2h", "h4": "4h", "h6": "6h", "h8": "8h", "h12": "12h",
            "d": "1D", "d1": "1D", "1d": "1D", "daily": "1D",
            "w": "1W", "w1": "1W", "1w": "1W", "weekly": "1W",
            "mn": "1M", "monthly": "1M", "1mo": "1M"}


def normalize_tf(tf: str) -> str:
    """'15m' / 'M15' / '15min' -> '15min'; 'H4'/'4H' -> '4h'; 'D' -> '1D';
    'W' -> '1W'; '1M' (capital) / 'MN' / '1mo' -> '1M' (month); '1m' -> '1min'.
    """
    s = str(tf).strip()
    if s in ("1M", "M", "MN", "1MN", "1Mo", "1mo", "monthly", "1MS", "MS"):
        return "1M"                                   # capital M = month (pandas)
    k = s.lower()
    if k == "1m":
        return "1min"                                 # lower-case m = minute
    if k in _ALIASES:
        return _ALIASES[k]
    m = re.fullmatch(r"(\d+)\s*(min|m|t)", k)
    if m:
        return f"{int(m.group(1))}min"
    m = re.fullmatch(r"(\d+)\s*h", k)
    if m:
        return f"{int(m.group(1))}h"
    if k in ("1d", "d"):
        return "1D"
    raise ValueError(f"unrecognised timeframe {tf!r}")


def tf_delta(tf: str) -> pd.Timedelta | None:
    """Nominal width for intraday tfs; None for 1D/1W/1M (calendar-defined)."""
    t = normalize_tf(tf)
    if t in ("1D", "1W", "1M"):
        return None
    return pd.Timedelta(t)


# ══ localisation helpers ══════════════════════════════════════════════════════
def _localize(naive_local, fallback_utc) -> pd.DatetimeIndex:
    """Naive NY wall-clock -> UTC. DST-ambiguous/non-existent instants (which on
    gold only occur on Sunday early mornings, when the venue is shut) fall back to
    `fallback_utc`."""
    idx = pd.DatetimeIndex(naive_local)
    loc = idx.tz_localize(TZ, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    fb = pd.DatetimeIndex(fallback_utc)
    out = pd.Series(loc).where(~pd.isna(loc), pd.Series(fb))
    return pd.DatetimeIndex(out).as_unit("ns")


def trading_day(times, open_hour: int = DEFAULT_DAY_OPEN_HOUR) -> pd.DatetimeIndex:
    """Trading-day label (naive local midnight of the day the session OPENED).

    With open_hour=18 a Monday-10:00 bar belongs to trading day *Sunday* (the
    session that opened Sunday 18:00). Delegates to `detectors.bias.trading_day`.
    """
    return _trading_day(pd.DatetimeIndex(times), TZ, open_hour)


def session_date(times, open_hour: int = DEFAULT_DAY_OPEN_HOUR) -> pd.DatetimeIndex:
    """The calendar date a session mostly trades on (trading_day + 1 day when the
    day opens in the evening). Monday's session -> Monday."""
    td = trading_day(times, open_hour)
    return td + pd.Timedelta(days=1) if open_hour >= 12 else td


# ══ bar builder ═══════════════════════════════════════════════════════════════
def _finish(g, label_utc, close_utc, extra: dict | None = None) -> pd.DataFrame:
    out = g.agg(open=("open", "first"), high=("high", "max"),
                low=("low", "min"), close=("close", "last"),
                n_m1=("open", "size"), first_m1=("_t", "min"), last_m1=("_t", "max"))
    out = out.reset_index(drop=True)
    out.index = pd.DatetimeIndex(label_utc).rename("time")
    out["close_time"] = pd.DatetimeIndex(close_utc)
    for k, v in (extra or {}).items():
        out[k] = np.asarray(v)
    out = out.dropna(subset=["open", "high", "low", "close"])
    out = out[~out.index.duplicated(keep="first")].sort_index()
    # the nominal end can never precede the last minute actually in the bar
    ct = pd.DatetimeIndex(out["close_time"]).tz_convert("UTC").as_unit("ns")
    lm = (pd.DatetimeIndex(out["last_m1"]) + pd.Timedelta(minutes=1)).tz_convert("UTC").as_unit("ns")
    out["close_time"] = ct.where(ct >= lm, lm)
    return out


def build_bars(m1: pd.DataFrame, tf: str, grid4h: str = DEFAULT_GRID_4H,
               day_open_hour: int = DEFAULT_DAY_OPEN_HOUR) -> pd.DataFrame:
    """Bars from ANY M1 frame. On the certified frame itself it returns the
    disk-cached `bars()` result (identical content), so a detector written as
    `detect(m1)` is fast on the full data and still correct on a truncated slice
    (which is what `probe_lookahead` feeds it). See `_build_bars` for the rules."""
    if _M1 is not None and m1 is _M1:
        return bars(tf, grid4h, day_open_hour)            # already a private copy
    return _build_bars(m1, tf, grid4h, day_open_hour)


def _build_bars(m1: pd.DataFrame, tf: str, grid4h: str = DEFAULT_GRID_4H,
                day_open_hour: int = DEFAULT_DAY_OPEN_HOUR) -> pd.DataFrame:
    """Pure bar builder. Works on ANY M1 frame (real, truncated, synthetic).

    Returns columns open, high, low, close, n_m1, first_m1, last_m1, close_time
    (+ trading_day for 1D/1W/1M), indexed by the nominal bar START in UTC.

    * <= 1h and dividing the hour: UTC-aligned (identical to NY-aligned, since
      New York's offset is a whole number of hours) — same buckets as
      `bars.resample`.
    * multi-hour (2h, 3h, 4h, 6h, 8h, 12h): buckets on the NY wall clock. 4h uses
      `grid4h`; the others are anchored on `day_open_hour`. `grid4h="utc"` gives
      a plain UTC resample for 4h.
    * 1D: the NY trading day rolling at `day_open_hour` (18:00 = venue candle).
    * 1W: ISO weeks of session dates (Sunday-evening session belongs to Monday's
      week); nominal close = Monday session open + 5 days.
    * 1M: calendar month of session date; nominal close = next month's first
      session open.
    Empty buckets are dropped (never forward-filled).
    """
    t = normalize_tf(tf)
    if grid4h not in GRIDS_4H:
        raise ValueError(f"grid4h must be one of {tuple(GRIDS_4H)}")
    if m1.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "n_m1",
                                     "first_m1", "last_m1", "close_time"])
    idx = pd.DatetimeIndex(m1.index).tz_convert("UTC")
    df = m1[["open", "high", "low", "close"]].copy()
    df["_t"] = idx
    one = pd.Timedelta(minutes=1)

    if t not in ("1D", "1W", "1M"):
        td = pd.Timedelta(t)
        hours = td / pd.Timedelta(hours=1)
        utc_aligned = (td <= pd.Timedelta(hours=1) and (pd.Timedelta(hours=1) % td)
                       == pd.Timedelta(0)) or (t == "4h" and grid4h == "utc")
        if utc_aligned:
            key = idx.floor(t)
            g = df.groupby(key, sort=True)
            labels = pd.DatetimeIndex(g.size().index)
            return _finish(g, labels, labels + td)
        if td < pd.Timedelta(hours=1) or hours != int(hours) or 24 % int(hours):
            raise ValueError(f"unsupported intraday timeframe {tf!r}")
        h = int(hours)
        off = GRIDS_4H[grid4h] if t == "4h" else day_open_hour % h
        local = idx.tz_convert(TZ).tz_localize(None)
        bucket = (local - pd.Timedelta(hours=off)).floor(f"{h}h") + pd.Timedelta(hours=off)
        g = df.groupby(bucket, sort=True)
        b = pd.DatetimeIndex(g.size().index)
        first = g["_t"].min().reindex(b)
        last = g["_t"].max().reindex(b)
        lab = _localize(b, first.to_numpy())
        clo = _localize(b + td, (last + one).to_numpy())
        return _finish(g, lab, clo, {"grid_open_local": b})

    tday = trading_day(idx, day_open_hour)
    shift = pd.Timedelta(days=1) if day_open_hour >= 12 else pd.Timedelta(0)
    if t == "1D":
        g = df.groupby(tday, sort=True)
        d = pd.DatetimeIndex(g.size().index)
        first = g["_t"].min().reindex(d)
        last = g["_t"].max().reindex(d)
        lab = _localize(d + pd.Timedelta(hours=day_open_hour), first.to_numpy())
        clo = _localize(d + pd.Timedelta(days=1, hours=day_open_hour),
                        (last + one).to_numpy())
        return _finish(g, lab, clo, {"trading_day": d})

    sdate = tday + shift
    if t == "1W":
        monday = sdate - pd.to_timedelta(sdate.dayofweek, unit="D")
        g = df.groupby(monday, sort=True)
        w = pd.DatetimeIndex(g.size().index)
        first = g["_t"].min().reindex(w)
        last = g["_t"].max().reindex(w)
        open_local = w - shift + pd.Timedelta(hours=day_open_hour)
        lab = _localize(open_local, first.to_numpy())
        clo = _localize(open_local + pd.Timedelta(days=5), (last + one).to_numpy())
        return _finish(g, lab, clo, {"trading_day": w - shift})
    # 1M
    month = sdate.to_period("M").to_timestamp()
    g = df.groupby(month, sort=True)
    mm = pd.DatetimeIndex(g.size().index)
    first = g["_t"].min().reindex(mm)
    last = g["_t"].max().reindex(mm)
    nxt = mm + pd.offsets.MonthBegin(1)
    lab = _localize(mm - shift + pd.Timedelta(hours=day_open_hour), first.to_numpy())
    clo = _localize(nxt - shift + pd.Timedelta(hours=day_open_hour), (last + one).to_numpy())
    return _finish(g, lab, clo, {"trading_day": mm - shift})


# ══ cached access ═════════════════════════════════════════════════════════════
def _atomic_write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    try:
        df.to_parquet(tmp)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def bars(tf: str, grid4h: str = DEFAULT_GRID_4H,
         day_open_hour: int = DEFAULT_DAY_OPEN_HOUR,
         m1: pd.DataFrame | None = None) -> pd.DataFrame:
    """Bars on the certified data (disk-cached), or on `m1` if given (memoised).

    Every row carries `close_time` — use it (or `asof`) for availability.
    Returns a COPY (copy-on-write, so it is cheap): editing it in place never
    changes what the harness's own lookups (`prior_hilo`, controls) read.
    """
    return _bars(tf, grid4h, day_open_hour, m1).copy(deep=False)


def _bars(tf: str, grid4h: str = DEFAULT_GRID_4H,
          day_open_hour: int = DEFAULT_DAY_OPEN_HOUR,
          m1: pd.DataFrame | None = None) -> pd.DataFrame:
    """The memoised frame itself — harness-internal, never handed to callers."""
    t = normalize_tf(tf)
    g = grid4h if t == "4h" else "-"
    if not is_certified(m1):
        key = (id(m1), t, g, day_open_hour)
        hit = _MEM.get(key)
        if hit is None or hit[0] is not m1:          # id() can be reused after GC
            hit = (m1, _build_bars(m1, t, grid4h, day_open_hour))
            _MEM[key] = hit
        return hit[1]
    key = ("cert", t, g, day_open_hour)
    if key in _MEM:
        return _MEM[key]
    path = CACHE_DIR / f"bars_{t}_{g}_{day_open_hour}_{data_signature()}.parquet"
    if os.environ.get("CONCEPT_LAB_CACHE_DISABLE"):
        out = _build_bars(load_m1(), t, grid4h, day_open_hour)
    elif path.exists():
        out = pd.read_parquet(path)
    else:
        out = _build_bars(load_m1(), t, grid4h, day_open_hour)
        _atomic_write_parquet(out, path)
    _MEM[key] = out
    return out


def warm_cache() -> list[str]:
    """Build every commonly used bar series once (run before launching agents)."""
    done = []
    for tf in ("1min", "3min", "5min", "15min", "30min", "1h", "2h", "1D", "1W", "1M"):
        bars(tf)
        done.append(tf)
    for g in GRIDS_4H:
        bars("4h", grid4h=g)
        done.append(f"4h/{g}")
    return done


_FP_SKIP_MODULES = ("numpy", "pandas", "scipy", "pyarrow", "builtins")


def _code_fp(obj, h, seen: set, depth: int = 0) -> None:
    """Feed a function's code, constants, closure values and the user-level
    functions / simple globals it references into hash `h` (recursively)."""
    if depth > 6 or id(obj) in seen:
        return
    seen.add(id(obj))
    if isinstance(obj, functools.partial):
        _code_fp(obj.func, h, seen, depth + 1)
        for a in list(obj.args) + sorted(obj.keywords.items()):
            _val_fp(a, h, seen, depth + 1)
        return
    fn = getattr(obj, "__func__", obj)
    code = getattr(fn, "__code__", None)
    if code is None:
        h.update(repr(type(obj)).encode())
        return
    mod = getattr(fn, "__module__", "") or ""
    if mod.split(".")[0] in _FP_SKIP_MODULES:
        h.update(f"{mod}.{getattr(fn, '__qualname__', '')}".encode())
        return

    def _code(c):
        h.update(c.co_code)
        h.update(repr(c.co_names).encode())
        for k in c.co_consts:
            if isinstance(k, types.CodeType):
                _code(k)
            else:
                h.update(repr(k).encode())
    _code(code)
    for d in (fn.__defaults__ or ()):
        _val_fp(d, h, seen, depth + 1)
    for cell in (fn.__closure__ or ()):
        try:
            _val_fp(cell.cell_contents, h, seen, depth + 1)
        except ValueError:                               # empty cell
            pass
    g = getattr(fn, "__globals__", {})

    def _names(c):
        out = list(c.co_names)
        for k in c.co_consts:
            if isinstance(k, types.CodeType):
                out += _names(k)
        return out
    for name in _names(code):
        if name in g:
            _val_fp(g[name], h, seen, depth + 1, name=name)


def _val_fp(v, h, seen, depth, name: str = "") -> None:
    if isinstance(v, (str, int, float, bool, type(None), bytes, tuple, frozenset)) and \
            len(repr(v)) < 10_000:
        h.update(f"{name}={v!r};".encode())
    elif isinstance(v, (list, dict, set)) and len(repr(v)) < 10_000:
        h.update(f"{name}={v!r};".encode())
    elif callable(v) and not isinstance(v, type) and not isinstance(v, types.ModuleType):
        _code_fp(v, h, seen, depth)


def build_fingerprint(build) -> str:
    """Hash of what `build` will compute: its code and the code of every user
    function it calls (recursively), its closure values and the simple globals it
    reads. Library internals (numpy/pandas) are named, not hashed."""
    h = hashlib.sha1()
    _code_fp(build, h, set())
    return h.hexdigest()[:10]


def _caller_script() -> str:
    for fr in inspect.stack()[2:]:
        f = fr.filename
        if not f.startswith(str(HERE)):
            return os.path.abspath(f) if os.path.exists(f) else f
    return "?"


def cache_frame(key: str, build, version: str = "1", script: str | None = None
                ) -> pd.DataFrame:
    """Compute-once for YOUR expensive detector output on the certified data.

    The file name carries `key`, the data signature, the calling script and a
    fingerprint of `build` (its code, the code of the functions it calls, closure
    values and simple globals — `build_fingerprint`). So two concepts that pick
    the same key never share a frame, and editing the detector (e.g. fixing a
    lookahead bug) rebuilds instead of silently returning the old frame. `key`
    should still name every parameter. Stored as parquet with an atomic rename,
    so parallel agents are safe. Only for frames derived from `load_m1()`.
    The returned frame carries `attrs["cache_fp"]`.
    """
    safe = re.sub(r"[^A-Za-z0-9_.=-]+", "_", key)
    who = script or _caller_script()
    fp = hashlib.sha1(f"{build_fingerprint(build)}|{who}".encode()).hexdigest()[:10]
    path = CACHE_DIR / f"user_{safe}_v{version}_{fp}_{data_signature()}.parquet"
    if not os.environ.get("CONCEPT_LAB_CACHE_DISABLE") and path.exists():
        out = pd.read_parquet(path)
    else:
        out = build()
        if not os.environ.get("CONCEPT_LAB_CACHE_DISABLE"):
            _atomic_write_parquet(out, path)
    out.attrs["cache_fp"] = fp
    return out


# ══ availability-safe lookups ═════════════════════════════════════════════════
def asof(frame: pd.DataFrame, times, avail_col: str = "close_time") -> pd.DataFrame:
    """For each time t, the LAST row of `frame` whose `avail_col` <= t.

    This is the only safe way to read a higher-timeframe bar at a lower-timeframe
    moment (trap 9: the HTF bar in progress is the future). Rows with nothing
    available (and NaT times) are NaN. The returned frame is indexed by `times` and carries
    `bar_start` (the source row's index) and `available_at`.
    """
    tt = pd.DatetimeIndex(times)
    if tt.tz is None:
        raise ValueError("times must be tz-aware (UTC)")
    av = pd.DatetimeIndex(frame[avail_col]).tz_convert("UTC")
    if not av.is_monotonic_increasing:
        order = np.argsort(utc_ns(av), kind="stable")
        frame = frame.iloc[order]
        av = av[order]
    tn = utc_ns(tt)
    pos = np.searchsorted(utc_ns(av), tn, side="right") - 1
    ok = (pos >= 0) & ~np.isnat(tn)          # NaT sorts last: it must never read a row
    out = frame.iloc[np.clip(pos, 0, None)].copy()
    out["bar_start"] = frame.index[np.clip(pos, 0, None)]
    out["available_at"] = av[np.clip(pos, 0, None)]
    out.index = tt
    if (~ok).any():
        out.loc[~ok, :] = np.nan
    return out


def close_time_of(bar_starts, tf: str, grid4h: str = DEFAULT_GRID_4H,
                  day_open_hour: int = DEFAULT_DAY_OPEN_HOUR,
                  m1: pd.DataFrame | None = None) -> pd.DatetimeIndex:
    """close_time for given bar starts (looked up in `bars(tf)`); raises if a
    start is not a bar of that series."""
    b = bars(tf, grid4h, day_open_hour, m1)
    s = pd.DatetimeIndex(bar_starts)
    ct = b["close_time"].reindex(s)
    if ct.isna().any():
        bad = s[ct.isna().to_numpy()][:3]
        raise KeyError(f"not bar starts of {tf}: {list(bad)}")
    return pd.DatetimeIndex(ct)
