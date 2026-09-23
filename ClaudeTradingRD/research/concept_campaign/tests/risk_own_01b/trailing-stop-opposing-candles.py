"""risk_own_01b / trailing-stop-opposing-candles (contested) — two trade_tests.

reading a (definition: stop moved to 0.5 of the opposing candle): 30m rung-0 CISD
  ("having entered on the 30-minute"); the opposing candle = the opposing-candle
  series the CISD closed through; stop = 50% of that series' high-low range
  instead of the swing extreme; target 2R from that tighter stop. The justification
  is directional ("I don't anticipate price to trade above 50% of this opposing
  candle"), which is exactly what the matched control tests: same stop and target
  distance at random moments. Claim +.
reading b (variant: mechanical trail to each new opposing candle): parents = 15m
  rung-0 CISD positions (protected-swing stop, 2R, 150min). While a parent is open
  (M1-resolved against the stop currently in force), each time a 15m bar CLOSES
  beyond a newly formed opposing candle (for a short: below the low of the most
  recent up-close candle formed after entry), that candle's extreme becomes the
  stop. Each such trail is an event: decide at that bar's close, continue with
  stop = the opposing candle's extreme, target = the parent target, hold = parent's
  remaining hold. Claim +: the trailed level holds better than a random stop at
  the same distance. Clustered by parent.
Params declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *   # noqa

TF_A = "30min"
TF_B = "15min"


def detect_a(m1):
    ev, _, b = cisd_book(m1, TF_A)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev.empty:
        return ev[cols]
    H, L = b["high"].to_numpy(float), b["low"].to_numpy(float)
    half = np.array([0.5 * (H[s_:e_ + 1].max() + L[s_:e_ + 1].min())
                     for s_, e_ in zip(ev["s_pos"].to_numpy(), ev["e_pos"].to_numpy())])
    out = ev[cols].copy()
    out["stop_px"] = half
    s = out["direction"].to_numpy()
    c = ev["confirm_close"].to_numpy()
    valid = s * (c - half) > 0          # the half level must sit behind the decision close
    return out[valid].reset_index(drop=True)


def detect_b(m1):
    ev, _, b = cisd_book(m1, TF_B)
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold", "parent"]
    tn, o, h, l_, c = m1_arrays(m1)
    N = len(tn)
    O, H, L, C = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    bstart = cl.data.utc_ns(b.index).astype(np.int64)
    bclose = cl.data.utc_ns(pd.DatetimeIndex(b["close_time"])).astype(np.int64)
    nb = len(b)
    hold_ns = pd.Timedelta(HOLD[TF_B]).value
    rows = []
    dec_all = cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"])).astype(np.int64)
    for dec, s, st0, cp in zip(dec_all, ev["direction"].to_numpy(), ev["stop_px"].to_numpy(float),
                               ev["conf_pos"].to_numpy()):
        i0 = np.searchsorted(tn, dec, side="left")
        if i0 >= N:
            continue
        entry = o[i0]
        risk = s * (entry - st0)
        if not risk > 0:
            continue
        tgt = entry + s * 2.0 * risk
        end = dec + hold_ns
        stop = st0
        cand = -1
        used = -1
        j = cp + 1
        alive = True
        while alive and j < nb and bclose[j] <= end:
            a0 = max(np.searchsorted(tn, bstart[j], side="left"), i0)
            a1 = np.searchsorted(tn, bclose[j], side="left")
            if a1 > a0:
                hh, ll = h[a0:a1], l_[a0:a1]
                if s > 0:
                    if (ll <= stop).any() or (hh >= tgt).any():
                        alive = False
                        break
                else:
                    if (hh >= stop).any() or (ll <= tgt).any():
                        alive = False
                        break
            # bar j closed with the parent open: trail check, then new opposing candle
            if cand > used:
                beyond = C[j] > H[cand] if s > 0 else C[j] < L[cand]
                if beyond:
                    new_stop = L[cand] if s > 0 else H[cand]
                    if s * (C[j] - new_stop) > 0 and bclose[j] < end:
                        rows.append((bclose[j], s, new_stop, tgt, end - bclose[j], dec))
                        stop = new_stop if s * (new_stop - stop) > 0 else stop
                    used = cand
            opposing = C[j] < O[j] if s > 0 else C[j] > O[j]
            if opposing:
                cand = j
            j += 1
    if not rows:
        return pd.DataFrame(columns=cols)
    r = np.array(rows, dtype=np.float64)
    t = pd.to_datetime(np.array([x[0] for x in rows], dtype=np.int64), utc=True)
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": np.array([x[1] for x in rows], dtype=int),
                        "stop_px": r[:, 2], "target_px": r[:, 3],
                        "max_hold": pd.to_timedelta(np.array([x[4] for x in rows], dtype=np.int64), unit="ns"),
                        "parent": np.array([x[5] for x in rows], dtype=np.int64)})
    return out.sort_values(["decision_time", "parent"], kind="stable").reset_index(drop=True)[cols]


def run_a():
    ev = cl.cache_frame(f"trail_a_{TF_A}", lambda: detect_a(cl.load_m1()))
    print("a:", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=HOLD[TF_A], claim="+")
    show(res)
    op = {"rules": ["30m rung-0 CISD (series_open, 2/2, max_wait 3), decide at the confirming close, enter next M1 open",
                    "stop = 50% of the opposing-candle series' high-low range (the run the CISD closed through), not the swing extreme",
                    "target 2R from that stop; hold 300min; events where the half level is not behind the close dropped",
                    "claim +: price does not return to the half -> beats matched random entries of the same geometry"],
          "params": {"tf": TF_A, **BASE_PARAMS, "max_hold": HOLD[TF_A], "half_basis": "series high-low (wicks)", "grid4h": "n/a"}}
    src = {"tf": "corpus: Nlw-PZhoViQ entered on the 30-minute (concept definition)",
           **{k: BASE_SRC for k in BASE_PARAMS}, "max_hold": HOLD_SRC,
           "half_basis": "declared-before-run: bodies-vs-wicks unstated in the corpus; wick range of the series",
           "grid4h": "declared-before-run: no 4h bars used"}
    src["rr"] = "corpus: Nlw-PZhoViQ (2R read from context, per the concept's ambiguity note); method_spec §5.3 2R floor"
    p = cl.write_result("trailing-stop-opposing-candles", "a", res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="No structural target detector: the 'fixed target the swing stop cannot reach at 2R' precondition is not applied; every CISD takes the half-level stop with a 2R target.")
    print("wrote", p)


def run_b():
    ev = cl.cache_frame(f"trail_b_{TF_B}", lambda: detect_b(cl.load_m1()))
    print("b:", len(ev), ev["parent"].nunique())
    probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, claim="+", cluster="parent")
    show(res)
    op = {"rules": ["parents: 15m rung-0 CISD, entry next M1 open, protected-swing stop, 2R target, 150min hold",
                    "parent alive = no hit of the stop currently in force / target on M1 up to the bar close",
                    "opposing candle = most recent candle after entry closing against the position; trail when a 15m bar closes beyond it; its extreme becomes the stop (never loosened)",
                    "event per trail: decide at that close, stop = opposing candle extreme, target = parent target, hold = parent remaining; clustered by parent",
                    "claim +: trailed levels hold better than random stops of the same distance"],
          "params": {"tf": TF_B, **BASE_PARAMS, "parent_hold": HOLD[TF_B], "trail_level": "opposing candle extreme", "grid4h": "n/a"}}
    src = {"tf": "corpus: concept timeframes ltf 15m; phase3 primary stack entry TF",
           **{k: BASE_SRC for k in BASE_PARAMS}, "parent_hold": HOLD_SRC,
           "trail_level": "corpus: u8bnmaih_hA variant 'that candle's high becomes the level that should not be hit'",
           "grid4h": "declared-before-run: no 4h bars used"}
    p = cl.write_result("trailing-stop-opposing-candles", "b", res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Tests the trail's premise (the level holds) per trail event, not the whole managed P&L path, which the static-stop harness cannot resolve.")
    print("wrote", p)


if __name__ == "__main__":
    run_a()
    run_b()
