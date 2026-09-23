"""no-reversal-means-still-going (guest: Alex's Options, 1XWyy6Q-_8Q, TheSTRAT).

Claim: 'if it doesn't reverse against you it is still going' - exit on an opposing 2 on the
framing timeframe, and stay in while none has printed.

Operationalisation (gate_test, claim '+'):
  trades   = 15m STRAT 2-2 reversals in the direction of timeframe continuity (price above
             the current trading-day open and the current hour open for longs, below both for
             shorts), triggered intrabar when price takes the prior (2d/2u) bar's extreme;
             stop at the other side of that prior bar (standard STRAT; the concept gives none).
  rows     = every 15m close after the trigger, while the trade is alive (stop not yet hit)
             and no opposing 2 has closed before this bar, up to 16 bars; the row at which
             the first opposing 2 closes is included (that is the doctrine's exit moment).
  each row = 'keep holding from here' : same direction, original stop, no target, 1h hold.
  gate     = the bar that just closed is NOT an opposing 2 ('still going').
  => does holding after a no-reversal close beat holding after an opposing-2 close
     (each control-adjusted)? Rows of one trade share a cluster id.

All parameters were fixed before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

TF = "15min"          # corpus 1XWyy6Q-_8Q: 'take the 15-minute 2-2' (framing TF of the example)
MAX_BARS = 16         # declared-before-run: follow each trade for at most 16 x 15m = 4h
HOLD = "1h"           # declared-before-run: horizon of each 'keep holding' row (4 framing bars)


def strat_types(b):
    H, L = b["high"].to_numpy(), b["low"].to_numpy()
    up = np.r_[False, H[1:] > H[:-1]]
    dn = np.r_[False, L[1:] < L[:-1]]
    return up & ~dn, dn & ~up          # 2u, 2d  (3 = both, 1 = neither; first bar undefined)


def strat_22_triggers(m1, tf):
    """Intrabar 2-2 reversal triggers: prior bar a 2d (2u), price takes its high (low)."""
    b = cl.build_bars(m1, tf)
    H, L = b["high"].to_numpy(), b["low"].to_numpy()
    is2u, is2d = strat_types(b)
    pos = b.index.searchsorted(m1.index.floor(tf), "right") - 1      # m1 -> its tf bar
    valid = (pos >= 2) & (b.index[np.clip(pos, 0, None)] == m1.index.floor(tf))
    p = np.clip(pos, 2, None)
    mh, ml = m1["high"].to_numpy(), m1["low"].to_numpy()
    longc = valid & is2d[p - 1] & (mh > H[p - 1]) & (H[p - 2] > H[p - 1])
    shortc = valid & is2u[p - 1] & (ml < L[p - 1]) & (L[p - 2] < L[p - 1])
    rows = []
    for d, c in ((1, longc), (-1, shortc)):
        idx = np.flatnonzero(c)
        if not len(idx):
            continue
        s = pd.Series(idx).groupby(p[idx]).first()                    # first trigger per bar
        k = s.index.to_numpy()
        i = s.to_numpy()
        rows.append(pd.DataFrame({
            "m1_pos": i, "bar": k, "direction": d,
            "stop_px": np.where(d == 1, L[k - 1], H[k - 1]),
            "target_px": np.where(d == 1, H[k - 2], L[k - 2])}))
    if not rows:
        return b, pd.DataFrame(columns=["m1_pos", "bar", "direction", "stop_px", "target_px"])
    tr = pd.concat(rows).sort_values("m1_pos").reset_index(drop=True)
    return b, tr


def tfc_ok(m1, tr):
    """Timeframe continuity: trigger close above (below) current trading-day and hour opens."""
    o = m1["open"].to_numpy()
    td = pd.Series(cl.trading_day(m1.index).to_numpy())
    day_open = pd.Series(o).groupby(td).transform("first").to_numpy()
    hr = pd.Series(m1.index.floor("1h"))
    hour_open = pd.Series(o).groupby(hr.to_numpy()).transform("first").to_numpy()
    i = tr["m1_pos"].to_numpy()
    c = m1["close"].to_numpy()[i]
    d = tr["direction"].to_numpy()
    return (np.sign(c - day_open[i]) == d) & (np.sign(c - hour_open[i]) == d)


def detect(m1):
    b, tr = strat_22_triggers(m1, TF)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "still_going",
            "trade_id"]
    if tr.empty:
        return pd.DataFrame(columns=cols)
    tr = tr[tfc_ok(m1, tr)].reset_index(drop=True)
    c = m1["close"].to_numpy()[tr["m1_pos"].to_numpy()]
    tr = tr[(tr["stop_px"] - c) * tr["direction"] < 0].reset_index(drop=True)
    t_trig = m1.index[tr["m1_pos"].to_numpy()] + pd.Timedelta(minutes=1)
    is2u, is2d = strat_types(b)
    ct = pd.DatetimeIndex(b["close_time"])
    nb = len(b)
    # stop-hit time of each trade (only ever compared with an earlier decision time)
    hit = pd.Series(pd.NaT, index=range(len(tr)), dtype="datetime64[ns, UTC]")
    for d, side in ((1, "below"), (-1, "above")):
        sel = np.flatnonzero(tr["direction"].to_numpy() == d)
        if len(sel):
            th = cl.touch(t_trig[sel], tr["stop_px"].to_numpy()[sel], side,
                          horizon=pd.Timedelta("2D"), m1=m1)
            hit.iloc[sel] = pd.DatetimeIndex(th["hit_time"]).tz_convert("UTC")
    hit_close = pd.DatetimeIndex(hit) + pd.Timedelta(minutes=1)
    out = []
    last_ct = ct[-1] if nb else None
    for n, (bar, d, sp) in enumerate(zip(tr["bar"], tr["direction"], tr["stop_px"])):
        for k in range(bar, min(bar + MAX_BARS, nb)):
            if ct[k] > m1.index[-1] + pd.Timedelta(minutes=1):
                break                                   # bar not closed in this data
            if not pd.isna(hit_close[n]) and hit_close[n] <= ct[k]:
                break                                   # stopped out before this close
            opp = bool(is2d[k]) if d == 1 else bool(is2u[k])
            out.append((ct[k], d, sp, not opp, int(t_trig[n].value)))
            if opp:
                break                                   # doctrine exits here
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px", "still_going",
                                    "trade_id"])
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"])
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = np.nan
    # the stop must still be on the losing side of the last close at the decision
    lc = m1["close"].to_numpy()[m1.index.searchsorted(
        ev["decision_time"] - pd.Timedelta(minutes=1), "right") - 1]
    ev = ev[(ev["stop_px"] - lc) * ev["direction"] < 0]
    ev = ev.sort_values(["decision_time", "trade_id"]).reset_index(drop=True)
    return ev[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"norev_strat22_{TF}_tfc_mb{MAX_BARS}", lambda: detect(cl.load_m1()))
    print("rows", len(ev), "trades", ev["trade_id"].nunique(), "still_going share",
          ev["still_going"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "still_going", mask_available_at="decision_time", max_hold=HOLD,
                       claim="+", cluster="trade_id")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                                   "verdict_detail", "exposure_bars", "ties", "ctrl_overlap")})
    op = {"rules": [
        "15m STRAT bar types vs prior bar: 2u (higher high, no lower low), 2d, 3 (both), 1",
        "entry: 2-2 reversal triggered intrabar - prior 15m bar a 2d (2u) and an M1 high "
        "(low) takes its high (low); decision at that M1 close; target of the setup (bar "
        "before the 2) must lie beyond the trigger",
        "timeframe continuity: trigger close above (below) the trading-day open and the "
        "current hour open",
        "stop: other side of the prior 2 bar (the concept gives no stop; standard STRAT)",
        "rows: each 15m close from the trigger bar on, while stop not hit and no earlier "
        "opposing 2, max 16 bars; the first opposing-2 close is included, then the trade "
        "ends. 3s against are ignored ('give a 3 time'). No partials (unsized).",
        "row trade: same direction, original stop, no target, 1h time exit",
        "gate still_going = the just-closed bar is not an opposing 2; cluster = trade"],
        "params": {"tf": TF, "max_bars": MAX_BARS, "max_hold": HOLD, "tfc": "1D+1h opens"}}
    src = {"tf": "corpus: 1XWyy6Q-_8Q 'take the 15-minute 2-2' (worked example framing TF)",
           "max_bars": "declared-before-run: follow each trade 4h",
           "max_hold": "declared-before-run: 4 framing bars per hold row",
           "tfc": "corpus: 1XWyy6Q-_8Q precondition 'actionable signal with timeframe "
                  "continuity' (yaml htf 1D; hour = next TF above 15m/30m)"}
    p = cl.write_result("no-reversal-means-still-going", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Harness has no signal-based exit, so the doctrine is tested as "
                              "its predictive core: holding on after a no-opposing-2 close vs "
                              "after the opposing-2 close it says to exit on.")
    print("wrote", p)
