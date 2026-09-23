"""Faithfulness/robustness verification of dont-trade-after-expansion reading b (scratch)."""
import os, sys, importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.environ.setdefault("CONCEPT_LAB_LEDGER", str(HERE / "verify_ledger.jsonl"))
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
SRC = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_02b/dont-trade-after-expansion.py")
sys.path.insert(0, str(SRC.parent))
spec = importlib.util.spec_from_file_location("dtae", SRC); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
import concept_lab as cl
from _common import ns, ONE_MIN

m1 = cl.load_m1()
ev = cl.cache_frame("dtae_b_5m_late20", lambda fn=M.detect_b: fn(cl.load_m1()))
# identical cache key/fn fingerprint may differ due to calling script; recompute if needed
print("n events", len(ev), ev["late_expanded"].mean())

t = ns(m1.index)
dec = ns(ev["decision_time"])
dirn = ev["direction"].to_numpy()
op_all = m1["open"].to_numpy(); cl_all = m1["close"].to_numpy()
k = np.searchsorted(t, dec, "left") - 1

def htf_state(period_starts_ns):
    """For each event: start of the in-progress HTF candle (array of ns) -> expanded flag, elapsed min, body-direction flag."""
    start = period_starts_ns
    # group id per m1 bar = index of candle start it belongs to
    return start

def gate_for(tf_min=None, starts=None, prev_hi=None, prev_lo=None):
    pass

# --- 1h components (UTC hour) ---
hour = np.int64(60) * ONE_MIN
hid = t // hour
hi = pd.Series(m1["high"].to_numpy()).groupby(hid).cummax().to_numpy()
lo = pd.Series(m1["low"].to_numpy()).groupby(hid).cummin().to_numpy()
start = (dec // hour) * hour
elapsed = (dec - start) // ONE_MIN
kk = np.clip(k, 0, None)
same = (k >= 0) & (t[kk] >= start)
run_hi = np.where(same, hi[kk], np.nan); run_lo = np.where(same, lo[kk], np.nan)
hb = cl.build_bars(m1, "1h")
prev = cl.asof(hb, pd.DatetimeIndex(start).tz_localize("UTC"))
ph, pl = prev["high"].to_numpy(float), prev["low"].to_numpy(float)
expanded = np.where(dirn == 1, run_hi > ph, run_lo < pl)
expanded = np.where(np.isnan(run_hi) | np.isnan(ph), False, expanded)
# candle open of in-progress hour and last close before decision
first_idx = np.searchsorted(t, start, "left")
c_open = np.where(same, op_all[np.clip(first_idx, 0, len(t)-1)], np.nan)
last_close = np.where(same, cl_all[kk], np.nan)
body_dir = np.where(dirn == 1, last_close > c_open, last_close < c_open)
assert np.array_equal(expanded & (elapsed >= 20), ev["late_expanded"].to_numpy()), "reconstruction mismatch"

def run(label, mask, **kw):
    e = ev.copy(); e["g"] = np.asarray(mask, bool)
    kw.setdefault("max_hold", "50min")
    r = cl.gate_test(e, "g", mask_available_at="decision_time", claim="-", **kw)
    h = r["halves"]; b = r.get("blocks", {})
    print(f"{label:55s} fire={e['g'].mean():.3f} n_g={int(e['g'].sum())} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] "
          f"{r['verdict']:12s} H1={h['H1']['diff']:+.4f} H2={h['H2']['diff']:+.4f} "
          f"B=" + ",".join(f"{b[x]['diff']:+.3f}" for x in ('B1','B2','B3','B4') if x in b)
          + f" ovl={r['ctrl_overlap']:.3f} ties={r['ties'].get('verdict_stop_first')}/{r['ties'].get('verdict_5050', r['ties'].get('verdict_coin'))}", flush=True)
    return r

which = sys.argv[1:] or ["base"]
if "base" in which:
    run("REPRO late_expanded (>=20)", ev["late_expanded"])
    run("expanded AND early (<20)", expanded & (elapsed < 20))
    run("expanded (any time)", expanded)
    run("late (>=20) regardless of expansion", elapsed >= 20)
    run("late (>=20) NOT expanded", (elapsed >= 20) & ~expanded)
    for L in (10, 30, 40, 45):
        run(f"expanded & elapsed>={L}", expanded & (elapsed >= L))
    run("expanded & >=20 & body in trade dir (expansion candle)", expanded & (elapsed >= 20) & body_dir)
    run("expanded & >=40 & body in trade dir (final third)", expanded & (elapsed >= 40) & body_dir)
if "tod" in which:
    run("REPRO w/ ctrl_tod_tol_min=30", ev["late_expanded"], ctrl_tod_tol_min=30)
    run("REPRO w/ hold_basis=bars", ev["late_expanded"], hold_basis="bars")
    # within-late comparison: among elapsed>=20 events, expanded vs not
if "within" in which:
    e2 = ev[elapsed >= 20].reset_index(drop=True); m2 = expanded[elapsed >= 20]
    e2 = e2.copy(); e2["g"] = m2
    r = cl.gate_test(e2, "g", mask_available_at="decision_time", claim="-", max_hold="50min")
    print("WITHIN late(>=20): expanded vs not", r["diff"], r["ci_lo"], r["ci_hi"], r["verdict"], r["halves"]["H1"]["diff"], r["halves"]["H2"]["diff"])
    e3 = ev[expanded].reset_index(drop=True).copy(); e3["g"] = (elapsed >= 20)[expanded]
    r = cl.gate_test(e3, "g", mask_available_at="decision_time", claim="-", max_hold="50min")
    print("WITHIN expanded: late vs early", r["diff"], r["ci_lo"], r["ci_hi"], r["verdict"], r["halves"]["H1"]["diff"], r["halves"]["H2"]["diff"])
if "h4" in which:
    for grid in ("forex", "futures"):
        b4 = cl.bars("4h", grid4h=grid)
        st_idx = b4.index.asi8 if b4.index.tz is not None else b4.index.asi8
        starts = np.asarray(b4.index.tz_convert("UTC").asi8 if b4.index.tz else b4.index.asi8)
        pos = np.searchsorted(starts, dec, "right") - 1
        cstart = starts[pos]
        ctime = ns(b4["close_time"])[pos]
        inside = dec < ctime
        el4 = (dec - cstart) // ONE_MIN
        prevb = cl.asof(b4, pd.DatetimeIndex(cstart).tz_localize("UTC"))
        p4h, p4l = prevb["high"].to_numpy(float), prevb["low"].to_numpy(float)
        # running hi/lo within the 4h candle up to decision
        gid = np.searchsorted(starts, t, "right") - 1
        h4 = pd.Series(m1["high"].to_numpy()).groupby(gid).cummax().to_numpy()
        l4 = pd.Series(m1["low"].to_numpy()).groupby(gid).cummin().to_numpy()
        same4 = (k >= 0) & (gid[kk] == pos) & inside
        rh = np.where(same4, h4[kk], np.nan); rl = np.where(same4, l4[kk], np.nan)
        ex4 = np.where(dirn == 1, rh > p4h, rl < p4l)
        ex4 = np.where(np.isnan(rh) | np.isnan(p4h), False, ex4)
        run(f"4h {grid}: expanded & elapsed>=80 (40min-left analog: 1/3)", ex4 & (el4 >= 80))
        run(f"4h {grid}: expanded & elapsed>=160 (final third)", ex4 & (el4 >= 160))
