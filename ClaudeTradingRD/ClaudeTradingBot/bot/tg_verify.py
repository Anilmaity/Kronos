"""Verify decoded channel GOLD biases against actual XAUUSD candles (reports/xau_m5_3y.csv).

Input: tg_channel/bias/decoded.json — a list of decoded calls, XAUUSD only:
  {"msg_id":8023,"date":"2026-05-15","bias":"short|long","entry":4310.0,
   "target":4285.0,            # optional stated target
   "invalidation":4330.0,      # optional stated stop/invalidation level
   "note":"D1 bias flipped short"}

For each call, scan the cached M5 candles for `horizon_days` after the post date and report:
  reached_target, MFE (max favourable excursion in bias direction, pts),
  MAE (max adverse excursion, pts), and a verdict. Aggregates a hit-rate scorecard.
This is the honest test: does the channel's directional bias actually play out in the data?
"""
import csv, json, os, datetime as dt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "reports", "xau_m5_3y.csv")
DECODED = os.path.join(ROOT, "tg_channel", "bias", "decoded.json")
HORIZON_DAYS = 3      # how long the call has to work
TARGET_PTS_DEFAULT = 20.0   # if no explicit target, "worked" = MFE >= this in bias dir


def load_candles():
    t, h, l, c = [], [], [], []
    with open(CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(r["time"][:10]); h.append(float(r["h"])); l.append(float(r["l"])); c.append(float(r["c"]))
    return t, np.array(h), np.array(l), np.array(c)


def verify(call, t, H, L):
    d0 = call["date"][:10]
    horizon = call.get("horizon_days", HORIZON_DAYS)   # HTF biases need weeks, not days
    d1 = (dt.date.fromisoformat(d0) + dt.timedelta(days=horizon)).isoformat()
    idx = [i for i, d in enumerate(t) if d0 <= d <= d1]
    if not idx:
        return {**call, "verdict": "no-data"}
    hi, lo = H[idx], L[idx]
    entry = call["entry"]; bias = call["bias"]
    if bias == "short":
        mfe = entry - lo.min()          # favourable = price falls
        mae = hi.max() - entry          # adverse = price rises
        tgt = call.get("target")
        hit = (lo.min() <= tgt) if tgt else (mfe >= TARGET_PTS_DEFAULT)
        inval = call.get("invalidation")
        invalidated = (hi.max() >= inval) if inval else False
    else:  # long
        mfe = hi.max() - entry
        mae = entry - lo.min()
        tgt = call.get("target")
        hit = (hi.max() >= tgt) if tgt else (mfe >= TARGET_PTS_DEFAULT)
        inval = call.get("invalidation")
        invalidated = (lo.min() <= inval) if inval else False
    # verdict: target reached before invalidation?
    if hit and not invalidated: v = "WIN"
    elif hit and invalidated:    v = "WIN-but-also-invalidated (order unknown)"
    elif invalidated:            v = "LOSS (invalidated, target not reached)"
    else:                        v = "open/partial"
    return {**call, "mfe_pts": round(mfe, 1), "mae_pts": round(mae, 1),
            "target_hit": bool(hit), "invalidated": bool(invalidated), "verdict": v}


def main():
    if not os.path.exists(DECODED):
        raise SystemExit(f"decode gold charts into {DECODED} first")
    calls = json.load(open(DECODED, encoding="utf-8"))
    t, H, L, C = load_candles()
    print(f"candles cover {t[0]} -> {t[-1]}  |  horizon {HORIZON_DAYS}d\n")
    print(f"{'id':>6} {'date':12s} {'bias':5s} {'entry':>8} {'target':>8} {'MFE':>6} {'MAE':>6}  verdict")
    res = []
    for call in calls:
        r = verify(call, t, H, L); res.append(r)
        print(f"{r['msg_id']:>6} {r['date'][:10]:12s} {r['bias']:5s} {r['entry']:>8.1f} "
              f"{(str(r.get('target')) if r.get('target') else '-'):>8} "
              f"{r.get('mfe_pts','-'):>6} {r.get('mae_pts','-'):>6}  {r['verdict']}")
    scored = [r for r in res if r["verdict"] in ("WIN",) or r["verdict"].startswith("LOSS")]
    wins = sum(1 for r in res if r["verdict"] == "WIN")
    if scored:
        print(f"\nScorecard: {wins}/{len(scored)} clean wins "
              f"({100*wins/len(scored):.0f}%)  |  avg MFE "
              f"{np.mean([r['mfe_pts'] for r in res if 'mfe_pts' in r]):.1f}pt  "
              f"avg MAE {np.mean([r['mae_pts'] for r in res if 'mae_pts' in r]):.1f}pt")
    json.dump(res, open(os.path.join(ROOT, "tg_channel", "bias", "scorecard.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
