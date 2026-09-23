"""Independent re-implementation of average-daily-range reading b (expansion-day band gate)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(HERE, "scratch_ledger_b.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
import numpy as np, pandas as pd
import concept_lab as cl
from _common import cisd_book

m1 = cl.load_m1()
# 1) baseline book (the concept is the gate, the baseline is the locked rung-0 CISD)
evb, _, _ = cisd_book(m1, "15min")
evb = evb[["decision_time", "available_at", "direction", "stop_px", "rr"]].copy()
print("baseline events", len(evb))

# 2) own daily table: trading day = NY date of (t+6h); day close = last M1 close
ny = m1.index.tz_convert("America/New_York")
td = (ny + pd.Timedelta(hours=6)).tz_localize(None).normalize()
close_ns = (m1.index + pd.Timedelta(minutes=1)).asi8
g = pd.DataFrame({"o": m1.open.to_numpy(), "h": m1.high.to_numpy(), "l": m1.low.to_numpy(),
                  "c": m1.close.to_numpy(), "td": td, "cns": close_ns})
day = g.groupby("td").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"),
                          n=("h", "size"), last_close=("cns", "max"))
day = day[day.n >= 600].copy()
day["rng"] = day.h - day.l
body = (day.c - day.o).abs()
# opposing run: for an up close, open - low; for down close, high - open
opp = np.where(day.c >= day.o, day.o - day.l, day.h - day.o)
day["is_exp"] = (body > 0) & (opp <= 1.0 * body)
rows = []
rng_ = day.rng.to_numpy(); ex = day.is_exp.to_numpy()
band = np.full(len(day), np.nan)
for i in range(len(day)):
    if i < 19: continue
    w = slice(i - 19, i + 1)
    e = rng_[w][ex[w]]
    if len(e) >= 3:
        band[i] = np.median(e)
day["band"] = band

# 3) running covered range at decision, from M1 bars closed by decision in the same trading day
g["rh"] = g.groupby("td")["h"].cummax(); g["rl"] = g.groupby("td")["l"].cummin()
dt = pd.DatetimeIndex(evb.decision_time); dns = dt.asi8
pos = np.searchsorted(g.cns.to_numpy(), dns, side="right") - 1
etd = (dt.tz_convert("America/New_York") + pd.Timedelta(hours=6)).tz_localize(None).normalize()
same = (pos >= 0) & (g.td.to_numpy()[np.clip(pos, 0, None)] == etd.to_numpy())
cov = np.where(same, g.rh.to_numpy()[pos] - g.rl.to_numpy()[pos], np.nan)
dpos = np.searchsorted(day.last_close.to_numpy(), dns, side="right") - 1
bnd = np.where(dpos >= 0, day.band.to_numpy()[np.clip(dpos, 0, None)], np.nan)
own = (dpos >= 0) & (day.index.to_numpy()[np.clip(dpos, 0, None)] == etd.to_numpy())
print("band read from event's own (in-progress) day:", int(own.sum()))
ok = np.isfinite(cov) & np.isfinite(bnd)
mine = evb[ok].reset_index(drop=True).copy()
mine["cov"] = cov[ok]; mine["band"] = bnd[ok]
mine["open_exp"] = mine["cov"] < mine["band"]
print("mine kept", len(mine), "gate rate", mine.open_exp.mean())

# 4) compare against original frame
import importlib.util
spec = importlib.util.spec_from_file_location("adr_orig", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b/average-daily-range.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
orig = mod.detect(m1)
print("orig kept", len(orig), "gate rate", orig.open_exp.mean())
mm = orig.merge(mine[["decision_time", "direction", "cov", "band", "open_exp"]], on=["decision_time", "direction"],
                how="outer", indicator=True, suffixes=("", "_m"))
print(mm["_merge"].value_counts().to_dict())
b = mm[mm._merge == "both"]
print("cov maxdiff", np.nanmax(np.abs(b["cov"] - b["day_covered"])), "band maxdiff", np.nanmax(np.abs(b["band"] - b["exp_band"])))
print("mask agree", (b.open_exp == b.open_exp_m).mean())
only = mm[mm._merge != "both"]; print(only[["decision_time", "_merge"]].head(10))

def run(ev, col, **kw):
    r = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold="150min", claim="+", **kw)
    print(kw, "n", r["n"], "diff %.4f [%.4f, %.4f] p %.3f" % (r["diff"], r["ci_lo"], r["ci_hi"], r["p"]), r["verdict"],
          "H1 %.4f H2 %.4f" % (r["halves"]["H1"]["diff"], r["halves"]["H2"]["diff"]),
          "gated_vs_ctrl %.4f compl_vs_ctrl %.4f" % (r["gated_vs_own_control"]["diff"], r["complement"]["vs_own_control"]["diff"]),
          "ties", r["ties"]["verdict_stop_first"] if "verdict_stop_first" in r["ties"] else r["ties"], "exp", r["exposure_bars"])
    return r
print("== original frame"); run(orig, "open_exp")
print("== my frame"); r = run(mine, "open_exp", keep_trades=True)
print("== my frame, TOD-held control"); run(mine, "open_exp", ctrl_tod_tol_min=30)
print("== my frame, bars hold"); run(mine, "open_exp", hold_basis="bars")
tr = r["_trades"]; tr.to_pickle(os.path.join(HERE, "trades_b.pkl")); print(tr.columns.tolist())
