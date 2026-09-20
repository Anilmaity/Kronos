"""ICT / microstructure features on S5 bid/ask bars. All causal unless noted.

Provides the vocabulary the strategy families need:
  resample()      S5 -> higher TF (M1/M5...) OHLC on mid, for HTF structure
  swings()        confirmed fractal swing highs/lows (lagged by k -> causal to use)
  fvg()           fair value gaps on a given OHLC series
  sessions/masks  Asian / London / NY UTC windows
  displacement    |c-o| > mult*ATR
"""
import numpy as np
from .engine import Bars


# ---- session windows (UTC) ----
SESSIONS = {
    "asia":   (0, 7),     # 00:00-07:00 UTC
    "london": (7, 12),    # 07:00-12:00
    "ny":     (12, 17),   # 12:00-17:00 (overlap+NY morning)
    "late":   (17, 21),   # 17:00-21:00
}


def session_mask(b: Bars, name):
    a, z = SESSIONS[name]
    return (b.hod >= a) & (b.hod < z)


def hours_mask(b: Bars, hours):
    h = np.asarray(hours)
    return np.isin(b.hod, h)


def resample_bars(d, seconds):
    """Aggregate a raw S5 bid/ask dict (schema from oanda_s5.load) into `seconds`-bars,
    preserving SEPARATE bid & ask OHLC so fills stay realistic at the higher timeframe.
    Returns a dict with the same schema as load() -> feed straight into Bars().
    Buckets align to epoch (UTC). Gaps simply produce missing buckets (the engine's
    gap_sec guard then prevents trades spanning them)."""
    import numpy as _np
    ts = d["ts"]
    bucket = ts // seconds
    chg = _np.concatenate(([0], _np.where(_np.diff(bucket) != 0)[0] + 1, [len(ts)]))
    K = len(chg) - 1
    out = {k: _np.empty(K, _np.float32) for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")}
    out["ts"] = _np.empty(K, _np.int64); out["vol"] = _np.empty(K, _np.int32)
    for k in range(K):
        s, e = chg[k], chg[k + 1]
        out["ts"][k] = ts[s]
        out["vol"][k] = d["vol"][s:e].sum()
        out["bo"][k] = d["bo"][s]; out["bc"][k] = d["bc"][e - 1]
        out["bh"][k] = d["bh"][s:e].max(); out["bl"][k] = d["bl"][s:e].min()
        out["ao"][k] = d["ao"][s]; out["ac"][k] = d["ac"][e - 1]
        out["ah"][k] = d["ah"][s:e].max(); out["al"][k] = d["al"][s:e].min()
    return out


def resample(b: Bars, seconds):
    """Aggregate S5 mid bars into `seconds`-bars. Returns dict with arrays
    o,h,l,c,vol,ts plus s5_idx = the S5 index of each HTF bar's LAST S5 bar
    (so a decision on HTF bar k is actionable from S5 index s5_idx[k]+1).
    Buckets align to epoch (UTC), gaps simply produce missing buckets."""
    bucket = (b.ts // seconds)
    # boundaries where bucket changes
    chg = np.concatenate(([0], np.where(np.diff(bucket) != 0)[0] + 1, [b.n]))
    K = len(chg) - 1
    o = np.empty(K); h = np.empty(K); l = np.empty(K); c = np.empty(K)
    vol = np.empty(K, np.int64); ts = np.empty(K, np.int64); last = np.empty(K, np.int64)
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    op = (b.ao + b.bo) * 0.5
    for k in range(K):
        s, e = chg[k], chg[k + 1]
        o[k] = op[s]; c[k] = b.mid[e - 1]
        h[k] = hi[s:e].max(); l[k] = lo[s:e].min()
        vol[k] = b.vol[s:e].sum(); ts[k] = b.ts[s]; last[k] = e - 1
    return {"o": o, "h": h, "l": l, "c": c, "vol": vol, "ts": ts, "s5_idx": last}


def swings(h, l, k=2):
    """Confirmed fractal swings. sh[i]=True if h[i] is the max of [i-k, i+k]
    (a swing high), sl[i] similarly. These are CENTERED (use only after i+k bars
    have formed -> reference them at index i+k or later to stay causal)."""
    n = len(h)
    sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    for i in range(k, n - k):
        seg_h = h[i - k:i + k + 1]
        seg_l = l[i - k:i + k + 1]
        if h[i] == seg_h.max() and (seg_h.argmax() == k):
            sh[i] = True
        if l[i] == seg_l.min() and (seg_l.argmin() == k):
            sl[i] = True
    return sh, sl


def fvg(o, h, l, c):
    """Fair value gaps on an OHLC series. Returns (bull, bear, top, bot):
    bull[i]=True if l[i] > h[i-2] (3-candle bullish gap); zone=[h[i-2], l[i]].
    bear[i]=True if h[i] < l[i-2]; zone=[h[i], l[i-2]]. Detected at bar i (causal)."""
    n = len(h)
    bull = np.zeros(n, bool); bear = np.zeros(n, bool)
    top = np.full(n, np.nan); bot = np.full(n, np.nan)
    for i in range(2, n):
        if l[i] > h[i - 2]:
            bull[i] = True; bot[i] = h[i - 2]; top[i] = l[i]
        elif h[i] < l[i - 2]:
            bear[i] = True; top[i] = l[i - 2]; bot[i] = h[i]
    return bull, bear, top, bot


def ema(x, period):
    out = np.empty(len(x)); a = 2.0 / (period + 1)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out
