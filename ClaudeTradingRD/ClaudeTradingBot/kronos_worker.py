"""Parallel Kronos forecast worker. Computes predicted horizon-close for a disjoint
slice of decision indices and writes {iso_timestamp: pred_close_h} to JSON. The
expensive (inference) part only; the aggregator replays trades. Runs in the Kronos
venv (Python 3.12, torch).

Usage: python kronos_worker.py <csv> <lookback> <pred_len> <stride> <sample_count>
                              <idx_start> <idx_end> <out_json> <model>
"""
import sys, os, json
os.environ.setdefault("OMP_NUM_THREADS", "2")
sys.path.insert(0, "C:/Projects/ClaudeProjects/ClaudeTradingBot")
sys.path.insert(0, "C:/Projects/ClaudeProjects/KronosModel")

import torch
torch.set_num_threads(2)
import pandas as pd
from kronos_backtest import load_bars, atr, _max_gap_hours
from model import Kronos, KronosTokenizer, KronosPredictor

csv, lookback, pred_len, stride, sample_count, idx_start, idx_end, out_json, model_name = (
    sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]),
    int(sys.argv[6]), int(sys.argv[7]), sys.argv[8], sys.argv[9])

bars = load_bars(csv)
t = [b[0] for b in bars]; o = [b[1] for b in bars]; h = [b[2] for b in bars]
l = [b[3] for b in bars]; c = [b[4] for b in bars]; n = len(c)
a = atr(h, l, c, 14)

tok = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
model = Kronos.from_pretrained(model_name)
predictor = KronosPredictor(model, tok, device="cpu", max_context=512)

out = {}
done = 0
i = idx_start
while i <= min(idx_end, n - 1 - pred_len):
    w_lo = i - lookback + 1
    if w_lo < 0 or a[i] <= 0:
        i += stride; continue
    if _max_gap_hours(t, w_lo, i + pred_len) > 72.0:
        i += stride; continue
    window_df = pd.DataFrame({"open": o[w_lo:i+1], "high": h[w_lo:i+1],
                              "low": l[w_lo:i+1], "close": c[w_lo:i+1]})
    x_ts = pd.Series(t[w_lo:i+1]); y_ts = pd.Series(t[i+1:i+1+pred_len])
    pred = predictor.predict(df=window_df, x_timestamp=x_ts, y_timestamp=y_ts,
                             pred_len=pred_len, T=1.0, top_p=0.9,
                             sample_count=sample_count, verbose=False)
    out[t[i].isoformat()] = {"pred_close_h": float(pred["close"].iloc[-1]),
                             "pred_high_max": float(pred["high"].max()),
                             "pred_low_min": float(pred["low"].min()),
                             "last_close": c[i]}
    done += 1
    if done % 25 == 0:
        print(f"[{idx_start}-{idx_end}] {done} done (i={i})", flush=True)
        with open(out_json, "w") as f:    # checkpoint
            json.dump(out, f)
    i += stride

with open(out_json, "w") as f:
    json.dump(out, f)
print(f"[{idx_start}-{idx_end}] DONE {done} windows -> {out_json}", flush=True)
