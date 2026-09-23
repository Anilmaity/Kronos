"""balance-area-poc-target (guest: HolyAngelBruv, 8Z2AbZLjunU; unit live_stream_guests_02).

Claim: once price has left a balance area and RE-ENTERS it, the first objective is the
point of control (POC), then the far edge.

Data limit, stated up front: the certified XAUUSD file has no volume (OHLC only, and
spot gold has no consolidated volume anyway). The balance area is therefore built from a
TIME-at-price (TPO) profile, the Market Profile analogue of the volume profile
(Dalton; pillar-02): this is a declared proxy, not the guest's volume profile.
  * balance area = the previous trading day's (18:00 NY roll) 70% value area; POC = its
    most-visited price bin. 100 equal bins over that day's range; every M1 bar adds one
    count to each bin its [low, high] overlaps; the value area grows from the POC by the
    larger neighbouring bin until it holds 70% of the counts.
  * during the current trading day: an M1 close outside the value area ("left"),
    then the first later M1 close back inside it ("re-enter", close-based reading of an
    undefined term). One event per day (the first re-entry).
  * outcome: M1 touch of the POC before the trading day ends.
  * null (declared before running): the same moment, the same distance and horizon, in
    the OPPOSITE direction (back out through the edge it re-entered). This holds time
    and local volatility fixed, so the statistic is "toward the POC rather than away".
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

NBINS = 100
VA_SHARE = 0.70
MIN_M1 = 600


def value_area(h, l, nb=NBINS, share=VA_SHARE):
    lo, hi = float(l.min()), float(h.max())
    if not hi > lo:
        return None
    w = (hi - lo) / nb
    i0 = np.clip(((l - lo) / w).astype(int), 0, nb - 1)
    i1 = np.clip(((h - lo) / w).astype(int), 0, nb - 1)
    diff = np.zeros(nb + 1)
    np.add.at(diff, i0, 1)
    np.add.at(diff, i1 + 1, -1)
    cnt = np.cumsum(diff)[:nb]
    poc = int(np.argmax(cnt))
    a = b = poc
    tot, need = cnt[poc], share * cnt.sum()
    while tot < need and (a > 0 or b < nb - 1):
        up = cnt[b + 1] if b < nb - 1 else -1
        dn = cnt[a - 1] if a > 0 else -1
        if up >= dn:
            b += 1
            tot += cnt[b]
        else:
            a -= 1
            tot += cnt[a]
    return lo + a * w, lo + (b + 1) * w, lo + (poc + 0.5) * w


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "poc", "vah", "val"]
    td = cl.trading_day(m1.index)
    tdv = td.to_numpy()
    days, starts = np.unique(tdv, return_index=True)
    ends = np.r_[starts[1:], len(tdv)]
    H = m1["high"].to_numpy(float)
    L = m1["low"].to_numpy(float)
    C = m1["close"].to_numpy(float)
    T = m1.index
    rows = []
    prev_va = None
    for s, e in zip(starts, ends):
        if prev_va is not None:
            val, vah, poc = prev_va          # value_area returns (VAL, VAH, POC)
            c = C[s:e]
            out = (c > vah) | (c < val)
            inside = ~out
            seen = np.maximum.accumulate(out)
            seen_prev = np.r_[False, seen[:-1]]
            k = np.flatnonzero(inside & seen_prev)
            if len(k):
                k = int(k[0])
                lastout = np.flatnonzero(out[:k])[-1]
                direction = -1 if c[lastout] > vah else 1
                dt = T[s + k] + pd.Timedelta(minutes=1)
                rows.append((dt, dt, direction, poc, vah, val))
        if e - s >= MIN_M1:
            va = value_area(H[s:e], L[s:e])
            if va is not None:
                prev_va = va
        # a stub day keeps the last real day's value area
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=cols)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"]).tz_convert("UTC")
    out["available_at"] = pd.DatetimeIndex(out["available_at"]).tz_convert("UTC")
    return out


def run_rate(ev):
    mkt = cl.get_market()
    m1 = cl.load_m1()
    t = pd.DatetimeIndex(ev["decision_time"])
    tgt = ev["poc"].to_numpy(float)
    pos = mkt.pos_at_or_after(t)
    px = mkt.o[np.minimum(pos, len(mkt.o) - 1)]
    # horizon: the M1 bars left in the event's trading day
    tdm = cl.trading_day(m1.index).to_numpy()
    tde = cl.trading_day(t).to_numpy()
    day_end = np.searchsorted(tdm, tde, side="right")
    nb = np.maximum(day_end - pos, 0)
    dist = tgt - px
    up = dist > 0
    obs = np.zeros(len(t))
    mir = np.zeros(len(t))
    for m, sd, osd in ((up, "above", "below"), (~up, "below", "above")):
        if m.any():
            obs[m] = cl.touch(t[m], tgt[m], sd, horizon_bars=nb[m])["hit"].to_numpy()
            mir[m] = cl.touch(t[m], px[m] - dist[m], osd, horizon_bars=nb[m])["hit"].to_numpy()
    keep = nb > 0
    print("events with no bars left in day:", int((~keep).sum()))
    obs[~keep] = np.nan
    return cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                        null=mir, predictors=ev)


if __name__ == "__main__":
    ev = cl.cache_frame("balance_poc_tpo_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = run_rate(ev)
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
              "verdict", "verdict_detail"):
        print(" ", k, res.get(k))
    op = {"rules": [
        "balance area = previous trading day's 70% TPO value area (18:00 NY roll), POC = "
        "most-visited of 100 equal price bins (M1 high-low overlap counts)",
        "event = first M1 close back inside the value area after an M1 close outside it, "
        "during the current trading day; direction toward the POC",
        "outcome: M1 touch of the POC before the trading day ends",
        "null: same moment, same distance and horizon, opposite direction"],
        "params": {"profile": "TPO (time at price) proxy for volume", "bins": NBINS,
                   "value_area_share": VA_SHARE, "balance": "previous trading day",
                   "reentry": "M1 close inside", "horizon": "rest of trading day",
                   "min_m1_per_day": MIN_M1, "null": "same-moment mirror level"}}
    src = {"profile": "declared-before-run: no volume in the certified file; TPO is the "
                      "Market Profile analogue of the volume profile",
           "bins": "declared-before-run: 100 equal bins over the day's range",
           "value_area_share": "declared-before-run: the standard 70% value area "
                               "(Dalton, Market Profile convention)",
           "balance": "declared-before-run: the unit gives no rule for how many sessions "
                      "make a balance area; one trading day is the smallest standard unit",
           "reentry": "corpus: 8Z2AbZLjunU 'you're going to want to target the point of "
                      "control' after re-entry; 're-enter' undefined -> close-based",
           "horizon": "declared-before-run: intraday setup, resolved within the session",
           "min_m1_per_day": "declared-before-run: stub days never define a balance "
                             "(README trap 6)",
           "null": "declared-before-run: same-moment mirror null holds volatility "
                   "(README trap 4)"}
    p = cl.write_result("balance-area-poc-target", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Volume is unavailable: the balance area and POC are "
                              "time-at-price (TPO) proxies, not the guest's volume profile. "
                              "Only the first objective (POC) is tested.")
    print(p)
