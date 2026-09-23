exec(open("v1.py").read().split("ev0 = detect_with()")[0].replace('d["blocks"] = {h: round(v["diff"], 4)', 'd["blocks"] = {h: round(v.get("diff") or np.nan, 4)'))
import inspect
src = inspect.getsource(tw.detect_a)
src = src.replace('"stop_px": float(run_ext), "poi": poi})', '"stop_px": float(run_ext), "poi": poi, "ce": ce, "c_k": C[k_ok], "t_k": ct[k_ok]})')
src = src.replace('cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "poi"]', 'cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "poi", "ce", "c_k", "t_k"]')
src = src.replace("def detect_a(", "def detect_geo(")
exec(src, tw.__dict__)
NS = 10**9
def placebo(tfname, fill_bars, seed, reps=3):
    g = tw.detect_geo(m1) if tfname == "15min" else None
    b = cl.build_bars(m1, tfname)
    ct = tw._ns(b["close_time"]); C = b["close"].to_numpy()
    mt = tw._ns(m1.index); ML, MH = m1["low"].to_numpy(), m1["high"].to_numpy()
    rng = np.random.default_rng(seed)
    rows = []
    bar_ns = int(pd.Timedelta(tfname).value)
    for e in g.itertuples(index=False):
        bull = e.direction == 1
        a = abs(e.c_k - e.ce); s = abs(e.ce - e.stop_px)
        lo = np.searchsorted(ct, e.t_k - 30 * 86400 * NS); hi = np.searchsorted(ct, e.t_k + 30 * 86400 * NS)
        for _ in range(reps):
            j = rng.integers(lo, max(lo + 1, hi - fill_bars - 1))
            lvl = C[j] - a if bull else C[j] + a
            stp = lvl - s if bull else lvl + s
            end = ct[min(len(ct) - 1, j + fill_bars)]
            m = tw._fill(mt, ML, MH, ct[j], end, lvl, bull, stp)
            if m is None: continue
            rows.append({"decision_time": mt[m] + 60 * NS, "direction": 1 if bull else -1, "stop_px": stp})
    out = pd.DataFrame(rows)
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True).dt.as_unit("ns")
    out["available_at"] = out["decision_time"]; out["rr"] = 2.0
    return out.sort_values("decision_time").reset_index(drop=True), g

pl, g = placebo("15min", 12, 11)
print("real events", len(g), "placebo fills", len(pl))
print("geometry a/s median", (abs(g.c_k - g.ce) / abs(g.ce - g.stop_px)).median())
run("PLACEBO_limit_touch", pl)
run("PLACEBO_limit_touch_tod30", pl, ctrl_tod_tol_min=30)
pl2, _ = placebo("15min", 12, 12)
run("PLACEBO_limit_touch_seed2", pl2)
json.dump(OUT, open(os.path.join(HERE, "v3_out.json"), "w"), default=str, indent=1)
