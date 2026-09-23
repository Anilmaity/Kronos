"""risk_own_02a / consolidation-range-no-trade (contested) — gate_test on the 15m rung-0 CISD book.

Claim (+): entries taken while the instrument is NOT in a daily consolidation beat
entries taken inside one ("gold is in a consolidation. Not going to watch it today";
stand aside until one side of the range is taken).
  reading a (range / inside-days signature, method_spec §2.7 'price staying inside one
            prior candle's range; an inside bar'): the box is the range of the latest
            completed real day j such that every completed real day after it (at least 2)
            stayed inside [low_j, high_j], searching back up to 20 days.
  reading b ('small days with small bodies', tDiwwMRWF2k variant): the last 3 completed
            real days each have range < ADR(20) (mean of the 20 real days before them)
            and |body| / range <= 0.5; the box is their combined high/low.
  consolidating = a box exists AND today's running high/low (M1 closed by the decision)
                  has not taken either side of it (wick counts as taken).
  gate (kept) = not consolidating; complement = entries taken inside the consolidation.
Params declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02a")
from _common import *   # noqa

MAX_BACK = 20
MIN_INSIDE = 2
SMALL_N = 3
ADR_LB = 20
BODY_CUT = 0.5


def boxes(m1):
    d = real_days(m1)
    h, l_ = d["high"].to_numpy(float), d["low"].to_numpy(float)
    o, c = d["open"].to_numpy(float), d["close"].to_numpy(float)
    n = len(d)
    ah = np.full(n, np.nan); al = np.full(n, np.nan)
    for i in range(n):
        for j in range(i - MIN_INSIDE, max(-1, i - MAX_BACK - 1), -1):
            if (h[j + 1:i + 1] <= h[j]).all() and (l_[j + 1:i + 1] >= l_[j]).all():
                ah[i], al[i] = h[j], l_[j]
                break
    rng = h - l_
    bh = np.full(n, np.nan); bl = np.full(n, np.nan)
    body_ok = np.abs(c - o) <= BODY_CUT * rng
    for i in range(SMALL_N - 1 + ADR_LB, n):
        w = slice(i - SMALL_N + 1, i + 1)
        adr = rng[i - SMALL_N + 1 - ADR_LB:i - SMALL_N + 1].mean()
        if (rng[w] < adr).all() and body_ok[w].all():
            bh[i], bl[i] = h[w].max(), l_[w].min()
    return pd.DataFrame({"ah": ah, "al": al, "bh": bh, "bl": bl}), d["close_time"]


def detect(m1):
    ev, _, _ = cisd_book(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    ev = ev[cols].copy()
    if ev.empty:
        return ev.assign(not_cons_a=pd.Series(dtype=bool), not_cons_b=pd.Series(dtype=bool))
    bx, avail = boxes(m1)
    r = asof_rows(bx, avail, ev["decision_time"])
    run = cl.running_hilo(ev["decision_time"], "1D", m1=m1)
    rh, rl = run["high"].to_numpy(), run["low"].to_numpy()
    have_run = np.isfinite(rh)
    # a decision always has at least one closed M1 of its day (it is a 15m close); keep all rows
    ok = have_run
    ev = ev[ok].reset_index(drop=True)
    rh, rl = rh[ok], rl[ok]
    r = r[ok].reset_index(drop=True)
    ca = np.isfinite(r["ah"].to_numpy()) & (rh <= r["ah"].to_numpy()) & (rl >= r["al"].to_numpy())
    cb = np.isfinite(r["bh"].to_numpy()) & (rh <= r["bh"].to_numpy()) & (rl >= r["bl"].to_numpy())
    ev["not_cons_a"] = ~ca
    ev["not_cons_b"] = ~cb
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"cons_{TF}_mb{MAX_BACK}_mi{MIN_INSIDE}_sn{SMALL_N}_adr{ADR_LB}_b{BODY_CUT}",
                        lambda: detect(cl.load_m1()))
    print(len(ev), (~ev[["not_cons_a", "not_cons_b"]]).mean().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe.get("passed"))
    base = {**BASE_PARAMS, "stub_day_min_n_m1": MIN_N_M1, "day_roll": "18:00 NY",
            "side_taken": "running trading-day high/low beyond the box (a wick counts)"}
    bsrc = {**BASE_SRC, "stub_day_min_n_m1": MIN_N_M1_SRC,
            "day_roll": "session_window_fit: settled 18:00 NY daily roll",
            "side_taken": "declared-before-run: corpus leaves wick vs close open ('whether a wick counts or a close is required is not stated')"}
    spec = {
        "a": ("not_cons_a",
              {"box": "range of latest completed real day that contains every later completed real day",
               "min_inside_days": MIN_INSIDE, "max_back_days": MAX_BACK},
              {"box": "method_spec §2.7: consolidation signature 'price staying inside one prior candle's range; an inside bar'",
               "min_inside_days": "declared-before-run: 'small days' plural -> at least 2 contained days",
               "max_back_days": "declared-before-run: about a month of daily candles"},
              "box = range of the latest completed real day j containing all (>= 2) later completed real days (search back 20 days)"),
        "b": ("not_cons_b",
              {"box": "combined high/low of the last 3 small days", "small_days": SMALL_N,
               "adr_lookback_days": ADR_LB, "body_cut_of_range": BODY_CUT},
              {"box": "corpus: tDiwwMRWF2k variant 'the disqualifying signature named here is small days with small bodies'",
               "small_days": "declared-before-run: 'small days' plural, 3 consecutive",
               "adr_lookback_days": "corpus: X4XSsv5CNqg ADR over ~a month of daily candles (declared-before-run, as in risk_own_01b)",
               "body_cut_of_range": "threshold_fits: 0.5 of the range (EQ) is the corpus's candle-size ceiling (grade A anchor)"},
              "box = combined H/L of the last 3 completed real days, each with range < ADR(20 days before them) and |body| <= 0.5 x range"),
    }
    for reading, (col, pp, ps, rule) in spec.items():
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD, claim="+")
        show(res)
        op = {"rules": [BASE_RULE, rule,
                        "consolidating = box exists and today's running high/low has not taken either side",
                        "gate = not consolidating; claim +: entries outside a consolidation beat entries inside"],
              "params": {**base, **pp}}
        p = cl.write_result("consolidation-range-no-trade", reading, res, operationalization=op,
                            params_source={**bsrc, **ps}, script=__file__, probe=probe,
                            notes=("The concept is an instrument-level 'stop watching' rule; tested as a "
                                   "gate on the 15m book because that is the only way a no-trade rule "
                                   "shows up in P&L. The range is drawn by eye in the corpus; both boxes "
                                   "are declared mechanisations. mask_available_at = decision time."))
        print("wrote", p)
