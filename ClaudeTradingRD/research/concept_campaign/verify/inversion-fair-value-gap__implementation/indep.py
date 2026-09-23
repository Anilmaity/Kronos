"""Independent re-implementation of inversion-fair-value-gap reading b from the YAML.
Written without reusing the campaign script's helpers."""
import os, sys
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

MAXW, RETEST, RR = 12, 16, 2.0

def bars15(m1):
    g = m1[["open","high","low","close"]].resample("15min", label="left", closed="left")
    b = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last()}).dropna()
    b["close_time"] = b.index + pd.Timedelta("15min")
    return b

def detect(m1, merge=True, skip_stop_bar=True):
    b = bars15(m1)
    end = m1.index[-1] + pd.Timedelta("1min")
    b = b[b.close_time <= end]
    h, l, c = b.high.values, b.low.values, b.close.values
    ct = b.close_time.values.astype("datetime64[ns]").astype(np.int64)
    n = len(b)
    inv = {}  # (j,d) -> [zlo, zhi, first_i]
    for i in range(2, n):
        if h[i] < l[i-2]:        # bearish FVG zone [h[i], l[i-2]] -> bullish inversion on close > l[i-2]
            zlo, zhi, d, far = h[i], l[i-2], 1, l[i-2]
        elif l[i] > h[i-2]:      # bullish FVG zone [h[i-2], l[i]] -> bearish inversion on close < h[i-2]
            zlo, zhi, d, far = h[i-2], l[i], -1, h[i-2]
        else:
            continue
        for j in range(i+1, min(i+MAXW, n-1)+1):
            if (d > 0 and c[j] > far) or (d < 0 and c[j] < far):
                key = (j, d) if merge else (j, d, i)
                if key in inv:
                    z = inv[key]; inv[key] = [min(z[0], zlo), max(z[1], zhi), min(z[2], i)]
                else:
                    inv[key] = [zlo, zhi, i]
                break
    mt = m1.index.values.astype("datetime64[ns]").astype(np.int64)
    mh, ml = m1.high.values, m1.low.values
    one = 60_000_000_000
    rows = []
    for key in sorted(inv):
        j, d = key[0], key[1]
        zlo, zhi, i = inv[key]
        ext = l[i-2:j+1].min() if d > 0 else h[i-2:j+1].max()
        if d * (c[j] - ext) <= 0:
            continue
        s0 = ct[j]
        s1 = ct[j+RETEST] if j + RETEST < n else mt[-1] + one
        a0, a1 = np.searchsorted(mt, s0), np.searchsorted(mt, s1)
        near = zhi if d > 0 else zlo
        for q in range(a0, a1):
            if (d > 0 and ml[q] <= near) or (d < 0 and mh[q] >= near):
                if skip_stop_bar and ((d > 0 and ml[q] <= ext) or (d < 0 and mh[q] >= ext)):
                    break
                rows.append((mt[q] + one, d, ext)); break
    ev = pd.DataFrame(rows, columns=["t","direction","stop_px"])
    t = pd.to_datetime(ev.t.values).tz_localize("UTC")
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": ev.direction.values, "stop_px": ev.stop_px.values, "rr": RR})
    out = out.drop_duplicates(["decision_time","direction"]).sort_values("decision_time").reset_index(drop=True)
    return out

if __name__ == "__main__":
    m1 = cl.load_m1()
    ev = detect(m1)
    ev.to_parquet("indep_events.parquet")
    o = pd.read_parquet("orig_events.parquet")
    k = ["decision_time","direction"]
    mg = ev.merge(o, on=k, how="outer", suffixes=("_i","_o"), indicator=True)
    print("indep", len(ev), "orig", len(o), mg["_merge"].value_counts().to_dict())
    both = mg[mg._merge=="both"]; print("stop mismatch", (np.abs(both.stop_px_i-both.stop_px_o)>1e-9).sum())
    res = cl.trade_test(ev, max_hold="150min", keep_trades=True)
    print({k: res.get(k) for k in ("verdict","n","diff","ci_lo","ci_hi","p","ci_method","halves")})
