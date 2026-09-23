"""Faithfulness verification: annotate each 1h CISD event with the poi_gate branch and variants."""
import os, sys
V = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/point-of-interest__faithfulness"
os.environ["CONCEPT_LAB_LEDGER"] = V + "/verify_ledger.jsonl"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
from _common import cl, np, pd, cisd_frame, OHLC
from detectors.poi import poi_gate, range_from_swing, fvg_pois, swing_pois

m1 = cl.load_m1()
b = cl.build_bars(m1, "1h")
ev = cisd_frame(b)
df = b[OHLC]
rows = []
for r in ev.itertuples(index=False):
    e = int(r.ext_pos); hold = max(0, int(r.conf_pos) - int(r.e_pos))
    res = poi_gate(df, e, r.direction, lookback=40, timeframe="1h", setup_type="reversal",
                   require_body_half_hold=True, body_hold_bars=hold)
    s = range_from_swing(df, e, r.direction, lookback=40)
    f_any = fvg_pois(df, s, e, r.direction)
    f_al = fvg_pois(df, s, e, r.direction, polarity="aligned")
    f_op = fvg_pois(df, s, e, r.direction, polarity="opposing")
    sw = swing_pois(df, s, e, r.direction)
    lowcol, hicol = df["low"].to_numpy(), df["high"].to_numpy()
    is_range_ext = (lowcol[e] <= lowcol[s:e+1].min()) if r.direction == "bullish" else (hicol[e] >= hicol[s:e+1].max())
    def gate(fv, sw_, fb_ok):
        hf, hs = bool(fv), bool(sw_)
        ft = any(p["tagged"] for p in fv); st = any(p["tagged"] for p in sw_)
        if hf and hs: return ft and st
        if hf: return ft
        if hs: return st
        return fb_ok
    fb_ok = bool(res.passed) if (not f_any and not sw) else False
    rows.append(dict(decision_time=b["close_time"].iloc[int(r.conf_pos)], poi_a=bool(res.passed),
        reason=res.reason, kinds=",".join(res.kinds_found), range_len=e - s, is_range_ext=bool(is_range_ext),
        n_fvg=len(f_any), n_fvg_tagged=sum(p["tagged"] for p in f_any), n_sw=len(sw), n_sw_tagged=sum(p["tagged"] for p in sw),
        a_aligned=gate(f_al, sw, bool(res.passed) if (not f_al and not sw) else None),
        a_opposing=gate(f_op, sw, None), fb_branch=(not f_any and not sw)))
out = pd.DataFrame(rows)
out.to_pickle(V + "/annot.pkl")
print(len(out)); print(out.reason.value_counts()); print(out.is_range_ext.mean())
