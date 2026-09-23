"""three-daily-profiles (guest: Jokerszn, JABOO4LYNjQ).

Claim: anticipate which profile the next daily candle will have; trade only when an
EXPANSION (one-sided delivery in the direction of daily order flow) is anticipated.
The only anticipation rules the speaker gives are the precondition (daily order flow
established) and the consolidation triggers (expect consolidation when any fires), so
"expansion anticipated in direction d" = order flow state d AND no consolidation
trigger at the close.

rate_test: P(next day is an expansion in direction d) vs the same outcome, same
direction, on a random other day within +/-30 days (regime-matched base rate).

Declared before the first run:
  expansion day in d   (close - open) * d >= 0.5 x ADR20 (ADR known at the open)
  order flow           _common.daily_orderflow (daily closes vs daily FVGs)
  consolidation cues   _common.consolidation_conditions (as consolidation-profile-conditions)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (cl, consolidation_conditions, daily, daily_orderflow,  # noqa: E402
                     np, pd, utc_ns)

CID = "three-daily-profiles"
EXP_BODY_ADR = 0.5


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction"]
    d = daily(m1)
    if len(d) < 30:
        return pd.DataFrame(columns=cols)
    of = daily_orderflow(d)["of_state"].to_numpy()
    cc = consolidation_conditions(m1, d)
    anyc = (cc["cond_htf"] | cc["cond_overext"] | cc["cond_eq"]).to_numpy()
    ok = (of != 0) & ~anyc & ~np.isnan(d["adr"].to_numpy())
    ct = pd.DatetimeIndex(d["close_time"])[ok]
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": of[ok].astype(int)}).reset_index(drop=True)


if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="300D")
    d = daily(m1)
    body = (d["close"] - d["open"]).to_numpy()
    adr_prev = d["adr"].shift(1).to_numpy()
    up = np.where(np.isnan(adr_prev), np.nan, (body >= EXP_BODY_ADR * adr_prev).astype(float))
    dn = np.where(np.isnan(adr_prev), np.nan, (-body >= EXP_BODY_ADR * adr_prev).astype(float))
    up_next, dn_next = np.append(up[1:], np.nan), np.append(dn[1:], np.nan)
    t_all = pd.DatetimeIndex(d["close_time"])
    ta = utc_ns(t_all)
    t = pd.DatetimeIndex(ev["decision_time"])
    te = utc_ns(t)
    pos = np.searchsorted(ta, te)
    sgn = ev["direction"].to_numpy()
    obs = np.where(sgn > 0, up_next[pos], dn_next[pos])
    valid = ~np.isnan(up_next)
    w = np.int64(30 * 86400e9)
    lo = np.searchsorted(ta, te - w, side="left")
    hi = np.searchsorted(ta, te + w, side="right")

    def null_fn(rng, k):
        out = np.full(len(te), np.nan)
        for i in range(len(te)):
            cand = np.arange(lo[i], hi[i])
            cand = cand[(cand != pos[i]) & valid[cand]]
            if len(cand) == 0:
                continue
            j = cand[rng.integers(len(cand))]
            out[i] = up_next[j] if sgn[i] > 0 else dn_next[j]
        return out

    print("events", len(ev), "long share", (sgn > 0).mean(), "base up", np.nanmean(up), "base dn", np.nanmean(dn))
    res = cl.rate_test(obs, t, available_at=ev["available_at"], null_fn=null_fn,
                       predictors=ev, claim="+")
    for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail"):
        print(k, res.get(k))
    op = {"rules": [
        "at each completed daily close (18:00 NY day, stubs < 600 M1 dropped)",
        "daily order flow = latest one-sided daily-close reaction to a live daily FVG (<= 60 days memory); must be non-neutral",
        "expansion anticipated in the order-flow direction when none of the consolidation triggers fire"
        " (first weekly H/L take this week; 3 same-direction closes or two ranges >= 1.5x ADR20; close within 0.40-0.60 of the daily dealing range)",
        "outcome: the NEXT day's body in that direction >= 0.5 x ADR20",
        "null: the same directional outcome on a random other day within +/-30 days"],
        "params": {"exp_body_adr": EXP_BODY_ADR, "adr_n": 20, "fvg_life_days": 60, "overext_mult": 1.5,
                   "eq_band": 0.10, "null_window_days": 30, "stub_min_m1": 600, "day_open_hour": 18}}
    src = {"exp_body_adr": "declared-before-run: 'one-sided delivery' as a body of at least half an average day",
           "adr_n": "declared-before-run: 20-day average daily range",
           "fvg_life_days": "declared-before-run: a daily FVG is a live PD array for 60 trading days",
           "overext_mult": "threshold_fits: displacement magnitude r=1.5 reused for 'large relative to average'",
           "eq_band": "declared-before-run: 'at the 0.5' of the dealing range as its middle fifth",
           "null_window_days": "phase3: +/-30 day regime-matched control window",
           "stub_min_m1": "declared-before-run: README trap 6 stub sessions",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="The speaker gives no positive test for anticipating expansion; the "
                        "anticipation is operationalised as order flow established and no consolidation trigger.")
    print("wrote", p)
