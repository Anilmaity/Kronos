"""Faithfulness / robustness sweep for opposing-run (verification only; not a result)."""
import sys, json
from pathlib import Path
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04a")
from _common import cl, np, pd, to_ts, M1, LiveCandle, ONE_MIN  # noqa

NB = int(sys.argv[1]) if len(sys.argv) > 1 else 500
m1 = cl.load_m1()
m = M1(m1)
PER = {"4h": 240, "1h": 60, "1D": None}


def events(lc, frac, per_min=None):
    st, ct = lc.bstart, lc.bclose
    per = (ct - st) if per_min is None else np.full(len(st), per_min * ONE_MIN)
    mid = (per * frac).astype(np.int64)
    tdec = st + mid
    keep = (tdec < ct) & (tdec <= m.t[-1] + ONE_MIN)
    tdec = tdec[keep]; bidx = np.flatnonzero(keep)
    hold = (ct[bidx] - tdec)
    s = lc.at(tdec)
    n_first = (np.searchsorted(m.t + ONE_MIN, tdec, side="right") - np.searchsorted(m.t, st[bidx], side="left"))
    ok = s["ok"] & (s["bucket"] == bidx) & (n_first >= 0.5 * mid[keep] / ONE_MIN)
    d = np.sign(s["price"] - s["open"]); ok &= d != 0
    rng = s["hi"] - s["lo"]; ok &= rng > 0
    opp = np.where(d > 0, s["open"] - s["lo"], s["hi"] - s["open"])
    body = np.abs(s["price"] - s["open"])
    stop = np.where(d > 0, s["lo"], s["hi"])
    t = to_ts(tdec)
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d, "stop_px": stop, "rr": np.nan,
                        "ratio": opp / np.where(rng > 0, rng, np.nan), "wb": opp / np.where(body > 0, body, np.nan),
                        "max_hold": pd.to_timedelta(hold, unit="ns")})[ok]
    out["direction"] = out["direction"].astype(int)
    return out.reset_index(drop=True)


def run(ev, mask, label, **kw):
    e = ev.copy(); e["g"] = mask
    mh = kw.pop("max_hold", None)
    if mh is None:
        r = cl.gate_test(e.drop(columns=["ratio", "wb"]), "g", mask_available_at="decision_time", n_boot=NB, **kw)
    else:
        r = cl.gate_test(e.drop(columns=["ratio", "wb", "max_hold"]), "g", mask_available_at="decision_time",
                         max_hold=mh, n_boot=NB, **kw)
    b = r.get("blocks") or {}
    row = dict(label=label, n=r["n"], fire=round(float(np.mean(mask)), 3), diff=round(r["diff"], 4),
               lo=round(r["ci_lo"], 4), hi=round(r["ci_hi"], 4), p=round(r["p"], 3), verdict=r["verdict"],
               H1=round(r["halves"]["H1"]["diff"], 4), H2=round(r["halves"]["H2"]["diff"], 4),
               blocks=[round(v["diff"], 3) for v in b.values()],
               g_vs_ctrl=round(r["gated_vs_own_control"]["diff"], 4),
               c_vs_ctrl=round(r["complement"]["vs_own_control"]["diff"], 4),
               overlap=round(r.get("ctrl_overlap") or 0, 3))
    print(json.dumps(row), flush=True)
    return row


rows = []
lcs = {}
for grid in ("forex", "futures"):
    lcs[("4h", grid)] = LiveCandle(m1, m, "4h", grid)
# baseline reproduce + grid
for grid in ("forex", "futures"):
    ev = events(lcs[("4h", grid)], 0.5, 240)
    rows.append(run(ev, (ev.ratio <= 0.30).to_numpy(), f"4h {grid} mid0.5 cut0.30", max_hold="120min"))
ev = events(lcs[("4h", "forex")], 0.5, 240)
for cut in (0.20, 0.25, 0.35, 0.40, 0.50):
    rows.append(run(ev, (ev.ratio <= cut).to_numpy(), f"4h forex mid0.5 cut{cut}", max_hold="120min"))
rows.append(run(ev, (ev.wb <= 1.0).to_numpy(), "4h forex mid0.5 opp/body<=1.0 (grade A)", max_hold="120min"))
rows.append(run(ev, (ev.ratio <= 0.30).to_numpy(), "4h forex mid0.5 cut0.30 tod30", max_hold="120min", ctrl_tod_tol_min=30))
rows.append(run(ev, (ev.ratio <= 0.30).to_numpy(), "4h forex mid0.5 cut0.30 bars", max_hold="120min", hold_basis="bars"))
for frac in (0.25, 0.375, 0.625, 0.75):
    e2 = events(lcs[("4h", "forex")], frac, 240)
    rows.append(run(e2, (e2.ratio <= 0.30).to_numpy(), f"4h forex mid{frac} cut0.30", max_hold=f"{int(240*(1-frac))}min"))
e3 = events(lcs[("4h", "futures")], 0.5, 240)
rows.append(run(e3, (e3.wb <= 1.0).to_numpy(), "4h futures mid0.5 opp/body<=1.0", max_hold="120min"))
# other corpus timeframes
lc1h = LiveCandle(m1, m, "1h")
e4 = events(lc1h, 0.5, 60)
rows.append(run(e4, (e4.ratio <= 0.30).to_numpy(), "1h mid0.5 cut0.30", max_hold="30min"))
json.dump(rows, open(Path(__file__).with_name("robust_rows.json"), "w"), indent=1)
