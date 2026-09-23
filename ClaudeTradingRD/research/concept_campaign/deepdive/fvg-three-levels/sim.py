"""Vectorised race / trade simulator for the fvg-three-levels deep dive.

Reproduces the campaign race exactly (hit = M1 extreme reaches target before the
first 15m CLOSE beyond the invalidation, within 16 15m closes after t; a hit on
the M1 bar that ends exactly at the invalidating 15m close counts as a miss) and
adds trade P&L variants. Read-only use of concept_lab.
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

RACE = 16
W = 262          # M1 bars gathered per row (16 x 15 = 240 plus slack)

_M = {}


def market():
    if not _M:
        m1 = cl.load_m1()
        mk = cl.get_market(m1)
        tn = np.asarray(mk.tn).view("int64")
        bucket = (tn // (15 * 60 * 10**9))             # UTC 15m bucket id (== NY 15m)
        last = np.r_[bucket[1:] != bucket[:-1], True]  # last M1 of its bucket
        bend = (bucket + 1) * (15 * 60 * 10**9)        # nominal close time
        m_end = tn + 60 * 10**9
        at_close = last & (m_end == bend)              # M1 close == 15m close time
        # bucket arrays
        bidx = np.cumsum(np.r_[True, bucket[1:] != bucket[:-1]]) - 1
        nb = bidx[-1] + 1
        blo = np.full(nb, np.inf); bhi = np.full(nb, -np.inf)
        np.minimum.at(blo, bidx, mk.l); np.maximum.at(bhi, bidx, mk.h)
        blast = np.flatnonzero(last)                   # M1 index of each bucket's last bar
        _M.update(mk=mk, m1=m1, last=last, at_close=at_close, bidx=bidx,
                  blo=blo, bhi=bhi, blast=blast, tn=tn)
    return _M


def pos(times):
    M = market()
    return cl.get_market(M["m1"]).pos_at_or_after(pd.DatetimeIndex(times))


def simulate(i0, d, up, dn, tie5050_seed=None, chunk=4000):
    """i0: M1 index of entry bar (first M1 at/after decision); d: +1/-1;
    up: target distance from entry open; dn: invalidation distance (15m close beyond
    entry - d*dn) and hard-stop distance.
    Returns dict of per-row arrays:
      hit      race outcome, harness convention (tie at the invalidating 15m close = miss)
      tie      hit bar == invalidating bar (ambiguous under the harness convention)
      inv      invalidated first
      R_close  trade: target limit / exit at the invalidating 15m close / time exit, in units of dn
      R_hard   trade: target limit / hard stop at entry - d*dn (M1, same-bar -> stop) / time exit
      tie_hard same-M1-bar stop+target ambiguity for R_hard
      R_hard50 R_hard with ties re-scored 50/50 (expected value: mean of win and loss)
      R_close50 R_close with the close-tie scored 50/50 in expectation
    """
    M = market(); mk = M["mk"]
    n = len(i0)
    out = {k: np.full(n, np.nan) for k in
           ("hit", "tie", "inv", "R_close", "R_hard", "tie_hard", "R_hard50", "R_close50", "entry")}
    N = len(mk.o)
    ar = np.arange(W)
    for s in range(0, n, chunk):
        sl = slice(s, min(s + chunk, n))
        ii = np.asarray(i0[sl]); dd = np.asarray(d[sl], float)
        uu = np.asarray(up[sl], float); nn = np.asarray(dn[sl], float)
        ok = (ii < N - W) & np.isfinite(uu) & np.isfinite(nn) & (nn > 0) & (uu > 0)
        ii2 = np.where(ok, ii, 0)
        J = ii2[:, None] + ar[None, :]
        E = mk.o[ii2]
        H = mk.h[J]; L = mk.l[J]; C = mk.c[J]; O = mk.o[J]
        last = M["last"][J]; atc = M["at_close"][J]
        # window: up to and including the 16th bucket close
        cnt = np.cumsum(last, axis=1)
        inwin = (cnt - last) < RACE          # bars before the 16th close, plus the 16th close bar
        endj = np.argmax(cnt >= RACE, axis=1)
        full = (cnt[:, -1] >= RACE)
        ok &= full
        tgt = E + dd * uu
        inv = E - dd * nn
        fav = np.where(dd[:, None] > 0, H >= tgt[:, None], L <= tgt[:, None]) & inwin
        adv_close = np.where(dd[:, None] > 0, C < inv[:, None], C > inv[:, None]) & last & inwin
        stop_hit = np.where(dd[:, None] > 0, L <= inv[:, None], H >= inv[:, None]) & inwin
        BIG = W + 5
        jh = np.where(fav.any(1), np.argmax(fav, 1), BIG)
        ji = np.where(adv_close.any(1), np.argmax(adv_close, 1), BIG)
        js = np.where(stop_hit.any(1), np.argmax(stop_hit, 1), BIG)
        rows = np.arange(len(ii))
        # harness race: hit time = M1 close; inv time = 15m nominal close.
        # a hit on the invalidating bar itself ties when that M1 closes exactly at the 15m close
        tie = (jh == ji) & (jh < BIG) & atc[rows, np.minimum(jh, W - 1)]
        hit = (jh < ji) | ((jh == ji) & (jh < BIG) & ~tie)
        invf = (ji < BIG) & ~hit
        # --- close-stop trade
        cend = C[rows, endj]
        cinv = C[rows, np.minimum(ji, W - 1)]
        R_win = uu / nn
        R_inv = dd * (cinv - E) / nn
        R_to = dd * (cend - E) / nn
        Rc = np.where(hit, R_win, np.where(invf, R_inv, R_to))
        Rc50 = np.where(tie, 0.5 * (R_win + R_inv), Rc)
        # --- hard stop trade
        oj = O[rows, np.minimum(js, W - 1)]
        gap = np.where(dd > 0, oj < inv, oj > inv)
        R_stop = np.where(gap, dd * (oj - E) / nn, -1.0)
        tie_h = (jh == js) & (jh < BIG)
        win_h = jh < js
        stop_h = (js < BIG) & (js <= jh)
        Rh = np.where(win_h, R_win, np.where(stop_h, R_stop, R_to))
        Rh50 = np.where(tie_h & ~gap, 0.5 * (R_win + R_stop), Rh)
        for k, v in (("hit", hit), ("tie", tie), ("inv", invf), ("R_close", Rc),
                     ("R_hard", Rh), ("tie_hard", tie_h), ("R_hard50", Rh50),
                     ("R_close50", Rc50), ("entry", E)):
            vv = v.astype(float)
            vv[~ok] = np.nan
            out[k][sl] = vv
    return out


def prior_extreme(i0, d, k):
    """Extreme of the last k COMPLETE 15m buckets before M1 index i0 (low for long, high
    for short), i.e. buckets whose last M1 bar is < i0."""
    M = market()
    nb_done = np.searchsorted(M["blast"], i0, side="left")   # buckets completed before i0
    lo = np.full(len(i0), np.inf); hi = np.full(len(i0), -np.inf)
    for j in range(1, k + 1):
        b = nb_done - j
        okb = b >= 0
        bb = np.where(okb, b, 0)
        lo = np.where(okb, np.minimum(lo, M["blo"][bb]), lo)
        hi = np.where(okb, np.maximum(hi, M["bhi"][bb]), hi)
    return np.where(np.asarray(d) > 0, lo, hi), np.where(np.asarray(d) > 0, hi, lo)


def day_codes(times):
    t = pd.DatetimeIndex(times)
    day = cl.trading_day(t)
    codes, uniq = pd.factorize(day)
    return codes, len(uniq)


def boot_ci(x, codes, nd, n_boot=2000, seed=7):
    """Trading-day cluster bootstrap of a mean (nan-ignoring)."""
    m = np.isfinite(x)
    x = x[m]; c = codes[m]
    s = np.bincount(c, weights=x, minlength=nd); n = np.bincount(c, minlength=nd)
    rng = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for b in range(n_boot):
        w = np.bincount(rng.integers(0, nd, nd), minlength=nd)
        bs[b] = (w * s).sum() / max((w * n).sum(), 1)
    mean = x.mean()
    lo, hi = np.percentile(bs, [2.5, 97.5])
    se = bs.std()
    p = 2 * min((bs <= 0).mean(), (bs >= 0).mean()) if mean != 0 else 1.0
    return mean, lo, hi, max(p, 1 / n_boot)
