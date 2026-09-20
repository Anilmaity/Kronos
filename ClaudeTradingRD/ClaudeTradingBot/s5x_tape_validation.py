"""s5x_tape_validation.py — replay account 5216074f's 67 real trades against the S5 tape.

No strategy building. Pure calibration:
  1. Are the 134 fill prices consistent with the S5 bid/ask tape?
  2. What effective spread did the account actually pay vs our 0.20-pt assumption?
  3. Per-trade MAE ("heat") at S5 resolution.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

import s5_engine as eng

HERE = os.path.dirname(os.path.abspath(__file__))
TRADES_CSV = os.path.join(HERE, "reports", "acct_5216074f_trades.csv")


def main():
    df = eng.load_s5()
    t = df["time"].values.astype("datetime64[ns]")
    n = len(df)

    tr = pd.read_csv(TRADES_CSV)
    tr["open_t"] = pd.to_datetime(tr["open_t"], utc=True).dt.tz_localize(None)
    tr["close_t"] = pd.to_datetime(tr["close_t"], utc=True).dt.tz_localize(None)
    assert len(tr) == 67, f"expected 67 trades, got {len(tr)}"

    def bar_index(ts):
        """Index of the S5 bar containing timestamp ts (bar covers [t_i, t_i+5s))."""
        i = int(np.searchsorted(t, np.datetime64(ts), side="right")) - 1
        if i < 0 or i >= n:
            return -1
        # tape has gaps (weekend/illiquid); require ts within 5s of bar start
        if (np.datetime64(ts) - t[i]) / np.timedelta64(1, "s") >= 5.0:
            return -1  # falls in a gap; use i anyway as "last known bar"? mark gap
        return i

    bid_l = df["bid_l"].values; bid_h = df["bid_h"].values
    ask_l = df["ask_l"].values; ask_h = df["ask_h"].values
    mid_l = df["mid_l"].values; mid_h = df["mid_h"].values
    mid_o = df["mid_o"].values; mid_c = df["mid_c"].values

    # ---------------------------------------------------------------- 1. fill-vs-bar check
    events = []  # (pid, kind, ts, px, side)
    for _, r in tr.iterrows():
        events.append((r.pid, "open", r.open_t, float(r.open_px), r.side))
        events.append((r.pid, "close", r.close_t, float(r.close_px), r.side))

    ev_rows = []
    n_in_ba, n_in_mid, n_gap = 0, 0, 0
    for pid, kind, ts, px, side in events:
        i = bar_index(ts)
        gap = i < 0
        if gap:
            # fall back to the last bar at/before ts (stale quote across a tape gap)
            i = max(0, int(np.searchsorted(t, np.datetime64(ts), side="right")) - 1)
            n_gap += 1
        in_ba = (bid_l[i] - 0.05) <= px <= (ask_h[i] + 0.05)
        in_mid = (mid_l[i] - 0.30) <= px <= (mid_h[i] + 0.30)
        n_in_ba += in_ba
        n_in_mid += in_mid
        ev_rows.append({
            "pid": int(pid), "event": kind, "time": str(ts), "px": px, "side": side,
            "bar_i": i, "bar_time": str(t[i]), "gap_bar": bool(gap),
            "bid_l": float(bid_l[i]), "ask_h": float(ask_h[i]),
            "mid_l": float(mid_l[i]), "mid_h": float(mid_h[i]),
            "inside_bidask_pm05": bool(in_ba), "inside_mid_pm030": bool(in_mid),
        })
    pct_ba = 100.0 * n_in_ba / len(events)
    pct_mid = 100.0 * n_in_mid / len(events)

    # ---------------------------------------------------------------- 2. effective spread
    # side-adjusted distance of ENTRY fill from the containing bar's mid path.
    # buys should fill above mid (pay half-spread), sells below.
    ent_d_range, ent_d_close = [], []
    for _, r in tr.iterrows():
        i = bar_index(r.open_t)
        if i < 0:
            i = max(0, int(np.searchsorted(t, np.datetime64(r.open_t), side="right")) - 1)
        px = float(r.open_px)
        # distance to the bar's mid RANGE (0 if inside): conservative lower bound
        if px > mid_h[i]:
            d_rng = px - mid_h[i]
        elif px < mid_l[i]:
            d_rng = px - mid_l[i]
        else:
            d_rng = 0.0
        d_cls = px - mid_c[i]
        sgn = 1.0 if r.side == "buy" else -1.0     # buy above mid => +, sell below mid => +
        ent_d_range.append(sgn * d_rng)
        ent_d_close.append(sgn * d_cls)
    ent_d_range = np.array(ent_d_range)
    ent_d_close = np.array(ent_d_close)
    med_half_range = float(np.median(ent_d_range))
    med_half_close = float(np.median(ent_d_close))

    # commission/spread residue: reported pnl vs pure price pnl at their lots
    sgn = np.where(tr["side"].values == "buy", 1.0, -1.0)
    pts = (tr["close_px"].values - tr["open_px"].values) * sgn
    price_pnl = pts * eng.DOLLARS_PER_POINT_PER_LOT * tr["vol"].values
    residue = tr["pnl"].values - price_pnl
    residue_per_lot = residue / tr["vol"].values
    med_residue_per_lot = float(np.median(residue_per_lot))
    tot_residue = float(residue.sum())

    # ---------------------------------------------------------------- 3. MAE / heat at S5 mid
    heats = []
    for _, r in tr.iterrows():
        i0 = max(0, int(np.searchsorted(t, np.datetime64(r.open_t), side="right")) - 1)
        i1 = max(i0, int(np.searchsorted(t, np.datetime64(r.close_t), side="right")) - 1)
        if r.side == "buy":
            worst_px = float(mid_l[i0:i1 + 1].min())
            adverse_pts = float(r.open_px) - worst_px          # >=0 if it went against
        else:
            worst_px = float(mid_h[i0:i1 + 1].max())
            adverse_pts = worst_px - float(r.open_px)
        adverse_pts = max(0.0, adverse_pts)
        heat_usd = adverse_pts * eng.DOLLARS_PER_POINT_PER_LOT * float(r.vol)
        heats.append({
            "pid": int(r.pid), "side": r.side, "vol": float(r.vol),
            "open_t": str(r.open_t), "close_t": str(r.close_t),
            "open_px": float(r.open_px), "close_px": float(r.close_px),
            "pnl": float(r.pnl), "bars_held": int(i1 - i0 + 1),
            "worst_adverse_mid": worst_px, "heat_pts": round(adverse_pts, 3),
            "heat_usd": round(heat_usd, 2),
            "price_pnl": round(float(price_pnl[len(heats)]), 2),
            "residue": round(float(residue[len(heats)]), 2),
        })
    h = np.array([x["heat_usd"] for x in heats])
    max_heat = float(h.max())
    p90_heat = float(np.percentile(h, 90))
    med_heat = float(np.median(h))
    n_gt30 = int((h > 30.0).sum())

    summary = {
        "n_trades": int(len(tr)),
        "n_fill_events": len(events),
        "n_events_in_gap_bars": n_gap,
        "fills_within_bidask_pm005_pct": round(pct_ba, 1),
        "fills_within_mid_pm030_pct": round(pct_mid, 1),
        "entry_dist_from_mid_range_median_pts": round(med_half_range, 4),
        "entry_dist_from_mid_close_median_pts": round(med_half_close, 4),
        "implied_one_way_cost_pts_range_basis": round(med_half_range, 4),
        "implied_round_trip_spread_pts_range_basis": round(2 * med_half_range, 4),
        "implied_round_trip_spread_pts_close_basis": round(2 * med_half_close, 4),
        "our_spread_assumption_pts": 0.20,
        "pnl_residue_total_usd": round(tot_residue, 2),
        "pnl_residue_median_per_lot_usd": round(med_residue_per_lot, 2),
        "our_commission_assumption_per_lot_rt": eng.COMMISSION_PER_LOT_RT,
        "heat_max_usd": round(max_heat, 2),
        "heat_p90_usd": round(p90_heat, 2),
        "heat_median_usd": round(med_heat, 2),
        "heat_gt_30usd_count": n_gt30,
        "reported_net_pnl": round(float(tr["pnl"].sum()), 2),
        "price_pnl_sum": round(float(price_pnl.sum()), 2),
    }

    path = eng.save_result("tape_validation", {
        "summary": summary,
        "fill_events": ev_rows,
        "per_trade_heat": heats,
    })

    print("saved ->", path)
    for k, v in summary.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
