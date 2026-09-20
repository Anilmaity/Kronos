"""Microstructure backtest engine for XAU 5-second bid/ask bars.

Design goals (per backtest-expert skill): pessimistic, no look-ahead, real
bid/ask fills, honest costs. Strategies emit *signals* (decision at bar close);
the engine resolves realistic fills and exits.

FILL MODEL (conservative):
  market long  -> next bar ASK open      market short -> next bar BID open
  limit  long  -> fills when ask_low <= level, at level (earns spread)
  limit  short -> fills when bid_high >= level, at level
EXIT MODEL (intrabar, SL checked before TP in the same bar):
  long  exit selling at BID:  SL if bid_low<=sl ; TP if bid_high>=tp
  short exit buying  at ASK:  SL if ask_high>=sl; TP if ask_low<=tp
  time stop after maxhold bars -> exit at close of that side.
Single position at a time (no pyramiding) — realistic for one challenge account.

P&L is in PRICE POINTS (long = exit-entry, short = entry-exit); spread is already
paid because entries/exits use the correct side. Convert to $ with dollars_per_point
(0.01 lot XAU = $1/pt, 0.10 lot = $10/pt). Commission is per-trade $ (round turn).
"""
import numpy as np


class Bars:
    """Column container for one contiguous run of S5 bid/ask bars."""

    __slots__ = ("ts", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "vol",
                 "mid", "spread", "n", "hod", "minute", "dow", "day")

    def __init__(self, d):
        for k in ("ts", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "vol"):
            setattr(self, k, d[k])
        self.mid = (self.bc + self.ac) * 0.5
        self.spread = self.ac - self.bc
        self.n = len(self.ts)
        # time-of-day features (UTC), computed once
        sec = self.ts % 86400
        self.hod = (sec // 3600).astype(np.int16)
        self.minute = (sec // 60).astype(np.int32)        # minute-of-day 0..1439
        self.dow = (((self.ts // 86400) + 4) % 7).astype(np.int8)  # 0=Mon..6=Sun
        self.day = (self.ts // 86400).astype(np.int64)     # epoch-day, for grouping


# ----------------------------------------------------------------------------
# vectorized indicators / primitives (all causal: value at i uses bars <= i)
# ----------------------------------------------------------------------------
def atr(b: Bars, period=14):
    """ATR on mid bars (points). Causal; atr[i] uses bars up to i."""
    h, l, c = b.ah.astype(np.float64), b.bl.astype(np.float64), b.mid.astype(np.float64)
    # use mid high/low approximations: true mid hi/lo not stored; use ask hi / bid lo
    hi = (b.ah + b.bh) * 0.5
    lo = (b.al + b.bl) * 0.5
    pc = np.empty(b.n); pc[0] = b.mid[0]; pc[1:] = b.mid[:-1]
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - pc), np.abs(lo - pc)))
    out = np.empty(b.n)
    a = 1.0 / period
    out[0] = tr[0]
    for i in range(1, b.n):
        out[i] = out[i - 1] + a * (tr[i] - out[i - 1])  # Wilder EMA
    return out


def roll_max(x, w):
    """Causal rolling max over previous w bars (excludes current): out[i]=max(x[i-w:i])."""
    out = np.full(len(x), np.nan)
    if w < 1:
        return out
    from numpy.lib.stride_tricks import sliding_window_view as swv
    if len(x) > w:
        out[w:] = swv(x[:-1], w).max(axis=1)
    return out


def roll_min(x, w):
    out = np.full(len(x), np.nan)
    if w < 1:
        return out
    from numpy.lib.stride_tricks import sliding_window_view as swv
    if len(x) > w:
        out[w:] = swv(x[:-1], w).min(axis=1)
    return out


def runs(ts, max_gap=30):
    """Split indices into contiguous runs where inter-bar gap <= max_gap sec.
    Returns list of (start,stop) index slices. Prevents trades spanning weekend
    or daily-break gaps."""
    if len(ts) == 0:
        return []
    brk = np.where(np.diff(ts) > max_gap)[0] + 1
    bounds = np.concatenate(([0], brk, [len(ts)]))
    return [(int(bounds[i]), int(bounds[i + 1])) for i in range(len(bounds) - 1)]


# ----------------------------------------------------------------------------
# signal container
# ----------------------------------------------------------------------------
class Signals:
    """Strategy output. Arrays aligned by signal, all same length.
      i        decision bar index (info up to & incl close[i] is allowed)
      side     +1 long / -1 short
      kind     0 market / 1 limit
      level    limit price (ignored for market)
      sl_pts   stop distance in points from fill (>0)
      tp_pts   target distance in points from fill (>0); use np.inf for trail-only
      ttl      bars a limit stays live before cancel (ignored for market)
    """
    def __init__(self, i, side, kind, level, sl_pts, tp_pts, ttl=None, meta=None):
        self.i = np.asarray(i, np.int64)
        self.side = np.asarray(side, np.int8)
        self.kind = np.asarray(kind, np.int8)
        self.level = np.asarray(level, np.float64)
        self.sl_pts = np.asarray(sl_pts, np.float64)
        self.tp_pts = np.asarray(tp_pts, np.float64)
        n = len(self.i)
        self.ttl = np.full(n, 120, np.int64) if ttl is None else np.asarray(ttl, np.int64)
        self.meta = meta or {}

    def __len__(self):
        return len(self.i)


# ----------------------------------------------------------------------------
# simulator
# ----------------------------------------------------------------------------
def simulate(b: Bars, sig: Signals, *, maxhold=240, dollars_per_point=1.0,
             commission=0.07, slippage_pts=0.0, trail_pts=0.0, be_at_pts=0.0,
             cooldown=0, gap_sec=30):
    """Resolve signals into trades. One position at a time, chronological.

    maxhold       time-stop in bars (240*5s = 20 min)
    commission    $ per round-turn trade
    slippage_pts  extra adverse points on every fill (market realism)
    trail_pts     if >0, trailing stop distance in points (ratchets favorably)
    be_at_pts     move stop to break-even once price travels this many pts in favor
    cooldown      bars to wait after a trade closes before a new entry
    Returns dict with trades array + metrics.
    """
    n = b.n
    order = np.argsort(sig.i, kind="stable")
    si, sside, skind = sig.i[order], sig.side[order], sig.kind[order]
    slevel, sslp, stpp, sttl = sig.level[order], sig.sl_pts[order], sig.tp_pts[order], sig.ttl[order]

    ao, al, ah, ac = b.ao, b.al, b.ah, b.ac
    bo, bl, bh, bc = b.bo, b.bl, b.bh, b.bc

    trades = []  # (entry_i, exit_i, side, entry, exit, sl, tp, pts, reason)
    busy_until = -1   # index up to which we are in a trade / cooldown
    k = 0
    N = len(si)
    while k < N:
        di = int(si[k]); side = int(sside[k]); k_kind = int(skind[k])
        if di <= busy_until:
            k += 1
            continue
        entry_idx = -1
        entry = np.nan
        # ---- entry resolution ----
        if k_kind == 0:  # market: next bar open
            j = di + 1
            if j >= n or b.ts[j] - b.ts[di] > gap_sec:  # don't cross a gap
                k += 1
                continue
            entry = (ao[j] if side > 0 else bo[j]) + slippage_pts * side
            entry_idx = j
        else:  # limit: scan forward up to ttl bars for a touch (no gap-cross)
            lvl = slevel[k]
            jmax = min(di + 1 + int(sttl[k]), n)
            j = di + 1
            while j < jmax:
                if b.ts[j] - b.ts[j - 1] > gap_sec:
                    break
                if side > 0 and al[j] <= lvl:
                    entry = lvl; entry_idx = j; break
                if side < 0 and bh[j] >= lvl:
                    entry = lvl; entry_idx = j; break
                j += 1
            if entry_idx < 0:
                k += 1
                continue
        # ---- stops/targets from fill ----
        sl = entry - side * sslp[k]
        tp = entry + side * stpp[k]
        trail_on = trail_pts > 0.0
        be_done = False
        best = entry  # most favorable price seen (for trailing/BE)
        # ---- walk forward to exit ----
        ex_idx = -1; ex = np.nan; reason = "time"
        hi_lim = min(entry_idx + maxhold, n)
        m = entry_idx + 1
        while m < hi_lim:
            if b.ts[m] - b.ts[m - 1] > gap_sec:   # gap -> close at prior close
                ex_idx = m - 1
                ex = bc[m - 1] if side > 0 else ac[m - 1]
                reason = "gap"
                break
            if side > 0:
                lo, hg = bl[m], bh[m]
                # SL first (conservative)
                if lo <= sl:
                    ex_idx = m; ex = sl; reason = "sl"; break
                if hg >= tp:
                    ex_idx = m; ex = tp; reason = "tp"; break
                # update favorable + trailing/BE on bid close
                if hg > best:
                    best = hg
                    if trail_on:
                        sl = max(sl, best - trail_pts)
                    if be_at_pts > 0 and not be_done and best - entry >= be_at_pts:
                        sl = max(sl, entry); be_done = True
            else:
                hg, lo = ah[m], al[m]
                if hg >= sl:
                    ex_idx = m; ex = sl; reason = "sl"; break
                if lo <= tp:
                    ex_idx = m; ex = tp; reason = "tp"; break
                if lo < best:
                    best = lo
                    if trail_on:
                        sl = min(sl, best + trail_pts)
                    if be_at_pts > 0 and not be_done and entry - best >= be_at_pts:
                        sl = min(sl, entry); be_done = True
            m += 1
        if ex_idx < 0:  # ran into maxhold
            ex_idx = min(hi_lim - 1, n - 1)
            ex = bc[ex_idx] if side > 0 else ac[ex_idx]
            reason = "time"
        pts = (ex - entry) * side - slippage_pts
        trades.append((entry_idx, ex_idx, side, entry, ex, sl, tp, pts, reason))
        busy_until = ex_idx + cooldown
        k += 1

    return _metrics(b, trades, dollars_per_point, commission)


def _metrics(b, trades, dpp, commission):
    if not trades:
        return {"trades": 0, "net$": 0.0, "wr": 0.0, "pf": 0.0, "exp_R": 0.0,
                "maxDD$": 0.0, "tlist": []}
    pts = np.array([t[7] for t in trades])
    pnl = pts * dpp - commission
    # R per trade = pts / initial stop distance
    rs = []
    for t in trades:
        sl_dist = abs(t[3] - t[5]) or np.nan
        rs.append(((t[4] - t[3]) * t[2]) / sl_dist if sl_dist else 0.0)
    rs = np.array(rs)
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    dd = eq - peak
    wins = pnl > 0
    gw = pnl[pnl > 0].sum(); gl = -pnl[pnl <= 0].sum()
    days = len(np.unique(b.day[[t[0] for t in trades]]))
    durs = np.array([b.ts[t[1]] - b.ts[t[0]] for t in trades]) / 60.0  # minutes
    return {
        "trades": len(trades),
        "net$": float(pnl.sum()),
        "wr": float(wins.mean() * 100),
        "pf": float(gw / gl) if gl > 0 else float("inf"),
        "exp_R": float(np.nanmean(rs)),
        "exp$": float(pnl.mean()),
        "maxDD$": float(-dd.min()),
        "avgwin$": float(pnl[pnl > 0].mean()) if wins.any() else 0.0,
        "avgloss$": float(pnl[pnl <= 0].mean()) if (~wins).any() else 0.0,
        "trades_per_day": len(trades) / max(days, 1),
        "days": days,
        "avg_min": float(durs.mean()),
        "pnl": pnl,
        "eq": eq,
        "tlist": trades,
    }
