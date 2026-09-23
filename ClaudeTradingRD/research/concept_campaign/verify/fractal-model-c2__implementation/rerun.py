import os, sys, pickle
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_01a")
from _common import cl, np, pd, OHLC, c2_events, ltf_cisd_inside
CFG = dict(htf="4h", ltf="15min", min_m1=60, hold="240min")
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
def detect(m1):
    b = cl.build_bars(m1, CFG["htf"], grid4h="forex")
    b = b[b["n_m1"] >= CFG["min_m1"]]
    lt = cl.build_bars(m1, CFG["ltf"])
    c2 = c2_events(b[OHLC])
    pos = b.index.get_indexer(pd.DatetimeIndex(c2["time"]))
    rows = b.iloc[pos].copy()
    rows["direction"] = c2["direction"].to_numpy()
    conf = ltf_cisd_inside(b, lt, rows)
    prev = b.iloc[np.maximum(pos - 1, 0)]
    bull = (rows["direction"] == "bullish").to_numpy()
    tgt = np.where(bull, np.maximum(prev["high"].to_numpy(), rows["high"].to_numpy()),
                   np.minimum(prev["low"].to_numpy(), rows["low"].to_numpy()))
    ct = pd.DatetimeIndex(rows["close_time"])
    out = pd.DataFrame({"decision_time": ct, "available_at": ct,
                        "direction": np.where(bull, 1, -1),
                        "stop_px": np.where(bull, rows["low"], rows["high"]).astype(float),
                        "target_px": tgt.astype(float),
                        "c2_start": rows.index, "c2_open": rows["open"].to_numpy(float),
                        "c2_close": rows["close"].to_numpy(float),
                        "c1_hi": prev["high"].to_numpy(float), "c1_lo": prev["low"].to_numpy(float),
                        "c2_hi": rows["high"].to_numpy(float), "c2_lo": rows["low"].to_numpy(float),
                        "conf": conf, "posok": pos > 0,
                        "c2_n_m1": rows["n_m1"].to_numpy()})
    return out
m1 = cl.load_m1()
allc2 = detect(m1)
allc2.to_pickle("allc2_orig.pkl")
ev = allc2[allc2.conf & allc2.posok][COLS].reset_index(drop=True)
print("n", len(ev), "fp", cl.frame_fingerprint(ev))
