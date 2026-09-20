"""test_edge_0.py — Paper-test of 'Mid-window spot-momentum continuation'.

Strategy under test:
  For each 15m window, at the last logged tick with >=180s to window_end,
  compute move = spot_now - spot_open(first tick of window).
  If |move| > THRESH, buy the move's direction on whichever of {Kalshi,Poly}
  shows the lower side-ask. Skip if best ask < FLOOR. One contract, hold to settle.

We score win THREE ways:
  (a) PROXY   : last-tick logged spot vs window-open logged spot (in-sample, optimistic).
  (b) KALSHI  : kalshi.settled_direction (its OWN BRR index) by close_time map.
  (c) POLY    : polymarket.settled_direction (Chainlink) by reconstructed slug.

Costs modeled: Polymarket 1.8% taker fee on notional (ask), applied when the
chosen venue is Poly. Kalshi: no explicit per-contract fee here beyond the ask
crossing (book spread is NOT in the logged mid — flagged as a forward-test gap).
The logged side-price is a MID, not an executable ask; this backtest therefore
OVERSTATES edge (you cross a spread up to ~13c live). Treat results as a ceiling.

Run: DRY_RUN=true .venv/Scripts/python.exe test_edge_0.py
"""
import csv
import sys
import datetime as dt

sys.path.insert(0, ".")
CSV = "journal/arb15m_log.csv"
POLY_FEE = 0.018  # 1.8% taker on notional (ask)


def parse_ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_windows():
    rows_by_win = {}
    with open(CSV, newline="") as f:
        for r in csv.DictReader(f):
            we = r["window_end"]
            try:
                r["_ts"] = parse_ts(r["ts"])
                r["_we"] = parse_ts(we)
                r["spot"] = float(r["spot"])
                for k in ("poly15m_up", "kalshi15m_up", "poly15m_down", "kalshi15m_down"):
                    r[k] = float(r[k]) if r[k] not in ("", None) else None
            except (ValueError, KeyError):
                continue
            rows_by_win.setdefault(we, []).append(r)
    for we in rows_by_win:
        rows_by_win[we].sort(key=lambda x: x["_ts"])
    return rows_by_win


def build_kalshi_map():
    """close_time ISO -> 'UP'/'DOWN' from finalized KXBTC15M markets."""
    from bot import kalshi
    out = {}
    ms = kalshi._markets("KXBTC15M", status="settled", limit=1000)
    for m in ms:
        ct = m.get("close_time")
        res = m.get("result")
        if ct and res in ("yes", "no"):
            out[ct] = "UP" if res == "yes" else "DOWN"
    return out


def poly_settled_for_window(we_iso, cache):
    """Reconstruct slug btc-updown-15m-<start_ts> and query Poly resolution."""
    if we_iso in cache:
        return cache[we_iso]
    from bot import polymarket
    end = parse_ts(we_iso)
    start_ts = int(end.timestamp()) - 900
    slug = f"btc-updown-15m-{start_ts}"
    try:
        res = polymarket.settled_direction(slug)
    except Exception:
        res = None
    cache[we_iso] = res
    return res


def replay(rows_by_win, thresh, floor, kmap, poly_cache, want_truth=False):
    """Return per-window fire records. side-ask = min over venues of the chosen
    side's logged price. Scoring done by caller."""
    fires = []
    for we_iso, rows in rows_by_win.items():
        if len(rows) < 2:
            continue
        s0 = rows[0]["spot"]
        # last row with >=180s to window_end
        entry = None
        for r in rows:
            if (r["_we"] - r["_ts"]).total_seconds() >= 180:
                entry = r
        if entry is None:
            continue
        move = entry["spot"] - s0
        if abs(move) <= thresh:
            continue
        side = "up" if move > 0 else "down"
        pk, pp = entry.get(f"kalshi15m_{side}"), entry.get(f"poly15m_{side}")
        cands = []
        if pk is not None:
            cands.append(("kalshi", pk))
        if pp is not None:
            cands.append(("poly", pp))
        if not cands:
            continue
        venue, ask = min(cands, key=lambda c: c[1])
        if ask < floor:
            continue
        rec = {
            "we": we_iso, "side": side.upper(), "venue": venue, "ask": ask,
            "move": move, "proxy_dir": "UP" if entry["spot"] - s0 > 0 else "DOWN",
            "kalshi_truth": kmap.get(we_iso),
        }
        if want_truth:
            rec["poly_truth"] = poly_settled_for_window(we_iso, poly_cache)
        fires.append(rec)
    return fires


def pnl_of(rec, win):
    """Per-contract pnl given win bool. Poly fee on notional when venue=poly."""
    ask = rec["ask"]
    fee = POLY_FEE * ask if rec["venue"] == "poly" else 0.0
    return (1.0 - ask - fee) if win else (-ask - fee)


def score(fires, truth_key, haircut=0.0):
    """Aggregate using rec[truth_key] as the winning direction.
    `haircut` adds cents to the ask paid (models crossing a real book spread that
    the logged MID hides). Returns dict. Separates DIRECTIONAL losers (bet wrong)
    from fee/haircut bleed on correct bets."""
    used = [r for r in fires if r.get(truth_key)]
    if not used:
        return None
    dir_losers = 0
    pnls = []
    win_pnls = []
    for r in used:
        won = r[truth_key] == r["side"]
        ask = min(0.99, r["ask"] + haircut)
        fee = POLY_FEE * ask if r["venue"] == "poly" else 0.0
        p = (1.0 - ask - fee) if won else (-ask - fee)
        pnls.append(p)
        if not won:
            dir_losers += 1
        else:
            win_pnls.append(p)
    wins = sum(1 for r in used if r[truth_key] == r["side"])
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
    worst = min(pnls) if pnls else 0.0
    total = sum(pnls)
    return {
        "n": len(used), "hit": wins / len(used), "wins": wins,
        "dir_losers": dir_losers, "ev_per": total / len(used),
        "total": total, "avg_win": avg_win, "worst": worst,
        "ratio": (abs(worst) / avg_win) if avg_win > 0 else float("inf"),
    }


def fmt(d):
    if not d:
        return "  (no resolvable settlements)"
    return (f"  n={d['n']:3d}  hit={d['hit']*100:5.1f}%  dir_losers={d['dir_losers']:2d}  "
            f"EV/contract={d['ev_per']*100:+6.2f}c  total={d['total']*100:+7.1f}c  "
            f"avgWin={d['avg_win']*100:+5.2f}c  worst={d['worst']*100:+6.1f}c  "
            f"loss:win={d['ratio']:.1f}:1")


def main():
    rows_by_win = load_windows()
    print(f"Loaded {len(rows_by_win)} windows from {CSV}")
    print("Fetching Kalshi finalized 15m settlements (own index)...")
    kmap = build_kalshi_map()
    print(f"  Kalshi close_time->result map: {len(kmap)} entries")
    poly_cache = {}

    # ---- BASE CASE: thresh=15, floor=0.86, full truth scoring ----
    print("\n=== BASE CASE  (move>$15, ask>=0.86) ===")
    fires = replay(rows_by_win, 15.0, 0.86, kmap, poly_cache, want_truth=True)
    print(f"Firing windows: {len(fires)}")
    if fires:
        avg_ask = sum(f["ask"] for f in fires) / len(fires)
        venues = {}
        for f in fires:
            venues[f["venue"]] = venues.get(f["venue"], 0) + 1
        print(f"avg ask={avg_ask:.3f}  venue mix={venues}")

    print("PROXY  (logged last-tick spot vs open) — in-sample, optimistic:")
    print(fmt(score(fires, "proxy_dir")))
    print("KALSHI settled_direction (BRR index):")
    ks = score(fires, "kalshi_truth")
    print(fmt(ks))
    print("POLY   settled_direction (Chainlink):")
    ps = score(fires, "poly_truth")
    print(fmt(ps))

    # disagreement / basis-break count among fires
    both = [f for f in fires if f.get("kalshi_truth") and f.get("poly_truth")]
    disagree = [f for f in both if f["kalshi_truth"] != f["poly_truth"]]
    print(f"\nBasis check: {len(both)} windows with BOTH venue settlements; "
          f"{len(disagree)} disagree (Kalshi BRR != Poly Chainlink)")

    # ---- ROBUSTNESS SWEEP (scored on Kalshi truth, the real money index) ----
    print("\n=== ROBUSTNESS SWEEP — scored on KALSHI settled_direction ===")
    print(f"{'thr':>4} {'floor':>5} | {'n':>4} {'hit%':>6} {'EV/c':>7} {'tot c':>7} {'worst':>6} {'L:W':>6}")
    for thr in (10.0, 15.0, 30.0):
        for floor in (0.80, 0.86, 0.90):
            fs = replay(rows_by_win, thr, floor, kmap, poly_cache, want_truth=False)
            d = score(fs, "kalshi_truth")
            if d:
                print(f"{thr:4.0f} {floor:5.2f} | {d['n']:4d} {d['hit']*100:6.1f} "
                      f"{d['ev_per']*100:+7.2f} {d['total']*100:+7.1f} "
                      f"{d['worst']*100:+6.1f} {d['ratio']:6.1f}")
            else:
                print(f"{thr:4.0f} {floor:5.2f} |  (none)")

    # ---- SPREAD HAIRCUT SENSITIVITY (logged price is a MID, real ask is worse) ----
    print("\n=== SPREAD-HAIRCUT SENSITIVITY (base set, scored on POLY+KALSHI truth) ===")
    print("Logged side-price is a MID. Live books show the real ask 1-4c worse and")
    print("the favored side often already at 0.96-0.99. Add haircut to ask paid:")
    print(f"{'haircut':>7} | {'KALSHI EV/c':>11} {'worst':>6} | {'POLY EV/c':>10} {'worst':>6}")
    for hc in (0.00, 0.02, 0.05, 0.10):
        kd = score(fires, "kalshi_truth", haircut=hc)
        pd = score(fires, "poly_truth", haircut=hc)
        print(f"{hc*100:5.0f}c  | {kd['ev_per']*100:+10.2f} {kd['worst']*100:+6.1f} | "
              f"{pd['ev_per']*100:+9.2f} {pd['worst']*100:+6.1f}")

    # ---- VERDICT vs deploy bar ----
    print("\n=== VERDICT ===")
    print("Deploy bar: net EV > +1c/contract AND max-loss:avg-win < ~6:1 AND")
    print("kill if real-settlement hit < ~92% OR directional losers > ~7.")
    for label, d in (("KALSHI", ks), ("POLY", ps)):
        if not d:
            continue
        kill = (d["hit"] < 0.92) or (d["dir_losers"] > 7)
        passes = (d["ev_per"] > 0.01) and (d["ratio"] < 6.0) and not kill
        print(f"{label}-truth EV={d['ev_per']*100:+.2f}c  hit={d['hit']*100:.1f}%  "
              f"dir_losers={d['dir_losers']}  L:W={d['ratio']:.1f}:1  -> "
              f"{'PASSES' if passes else 'FAILS'} (kill={kill})")


if __name__ == "__main__":
    main()
