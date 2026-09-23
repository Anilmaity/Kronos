"""market-structure-shift — trade_test, two readings (contested: older vs later canon).

(a) EARLIEST RECORDINGS: in a downtrend (the broken swing high is a LOWER high than the
    swing high before it), a 15m CLOSE above that lower high (displacement resolved as a
    close beyond the pivot) whose displacing leg left a bullish FVG; the FVG is the entry:
    first return to the most recent such gap's near edge within 16 x 15m bars after the break
    -> long, stop = the leg's low (the extreme the shift turned on), 2R. Mirror for bearish.
(b) LATER CANON: stop raid first — the leg low swept the last confirmed swing low before it —
    then a 15m CLOSE above the last confirmed swing high; then enter on the retracement into
    the displacement range's discount: first return to 50% of [leg low, leg high-at-break]
    within 16 bars -> long, stop = the swept extreme, 2R. (No lower-high or FVG requirement;
    the canon's HTF-level-engagement precondition is not modelled.)
15m execution ("the 15-minute ... is what he recommends"), hold 10 x 15m.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ns, empty, bar_arrays, fvg_arrays, M1, first_touch, ONE_MIN  # noqa: E402

CID = "market-structure-shift"
TF, WAIT, HOLD, RR, RIGHT = "15min", 16, "150min", 2.0, 2
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def breaks(d: dict) -> list:
    """Every close through the most recent confirmed swing (first close only).
    Returns (dir, k, cur, prev_same_swing, anchor_pos, anchor_px, last_opp_swing)."""
    h, l, c, sh, sl = d["h"], d["l"], d["c"], d["sh"], d["sl"]
    n = len(h)
    out = []
    for bull in (True, False):
        piv, opp = (sh, sl) if bull else (sl, sh)
        cur, prev, broken = -1, -1, True
        opp_list = []
        for j in range(n):
            if cur >= 0 and not broken:
                lvl = h[cur] if bull else l[cur]
                if (c[j] > lvl) if bull else (c[j] < lvl):
                    broken = True
                    seg = l[cur:j + 1] if bull else h[cur:j + 1]
                    a = cur + int(np.argmin(seg) if bull else np.argmax(seg))
                    # last confirmed opposite swing strictly before the anchor bar (confirmed by a-1)
                    lo = [s for s in opp_list if s + RIGHT <= a - 1]
                    out.append((1 if bull else -1, j, cur, prev, a, float(seg.min() if bull else seg.max()),
                                lo[-1] if lo else -1))
            q = j - RIGHT
            if q >= 0 and piv[q]:
                prev, cur, broken = cur, q, False
            if q >= 0 and opp[q]:
                opp_list.append(q)
    return out


def make_detect(reading: str):
    def detect(m1: pd.DataFrame) -> pd.DataFrame:
        b = cl.build_bars(m1, TF)
        if len(b) < 30:
            return empty(COLS)
        d = bar_arrays(b)
        h, l = d["h"], d["l"]
        bull_g, bear_g, glo, ghi = fvg_arrays(h, l)
        m = M1(m1)
        ct = d["ct"]
        rows = []
        for dr, k, cur, prev, a, L, lastopp in breaks(d):
            up = dr == 1
            if reading == "a":
                if prev < 0 or not ((h[cur] < h[prev]) if up else (l[cur] > l[prev])):
                    continue                                   # not a lower high / higher low
                g = bull_g if up else bear_g
                cand = [i for i in range(a + 2, k + 1) if g[i]]
                if not cand:
                    continue                                   # no FVG left by the displacing leg
                i = cand[-1]
                level = ghi[i] if up else glo[i]
            else:
                if lastopp < 0 or not ((L < l[lastopp]) if up else (L > h[lastopp])):
                    continue                                   # no stop raid before the break
                ext = h[a:k + 1].max() if up else l[a:k + 1].min()
                level = 0.5 * (L + ext)
            t0 = ct[k]
            t1 = ct[min(k + WAIT, len(ct) - 1)]
            if t1 <= t0:
                continue
            j = first_touch(m, t0, t1, level, up, cancel=L)
            if j < 0:
                continue
            if (m.l[j] <= L) if up else (m.h[j] >= L):
                continue
            rows.append((m.t[j] + ONE_MIN, dr, L))
        if not rows:
            return empty(COLS)
        out = pd.DataFrame(rows, columns=["t", "direction", "stop_px"])
        t = pd.DatetimeIndex(pd.to_datetime(out["t"].to_numpy(np.int64), utc=True))
        return pd.DataFrame({"decision_time": t, "available_at": t, "direction": out["direction"].to_numpy(),
                             "stop_px": out["stop_px"].to_numpy(), "rr": RR}
                            ).sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)[COLS]
    return detect


RULES = {
    "a": ["15m bars, 2/2 fractal swings; bullish MSS = first 15m close above the most recent confirmed swing high, "
          "which must be LOWER than the confirmed swing high before it (downtrend); mirror bearish",
          "the displacing leg (leg low bar .. break bar) must contain a bullish 3-bar FVG (stamped at its 3rd candle "
          "<= the break bar); entry = first M1 return to the latest such gap's near edge within 16 x 15m after the break",
          "stop = leg low (extreme the shift turned on), 2R, hold 10 x 15m; return bars through the stop dropped"],
    "b": ["15m bars, 2/2 fractal swings; bullish MSS = first 15m close above the most recent confirmed swing high, "
          "where the leg low swept the last confirmed swing low before it (stop raid); mirror bearish",
          "entry = first M1 return to 50% of [leg low, highest high from leg low to the break bar] within 16 x 15m after "
          "the break (discount of the displacement range)",
          "stop = the swept extreme (leg low), 2R, hold 10 x 15m; return bars through the stop dropped"]}
SRC = {"tf": "corpus: YAML 'the 15-minute is less noisy and is what he recommends to most people'; timeframes htf [15m, 5m]",
       "swing": "phase3: 2/2 fractal swings (§1.8)",
       "wait": "declared-before-run: the entry retracement must come within 16 x 15m (4 trading hours) of the break",
       "rr": "phase3: 2R (the targets 'old high/low' are not mechanically defined)",
       "max_hold": "phase3: 10 entry-TF bars",
       "displacement": "threshold_fits: §2 displacement component (a) = a close beyond the pivot (grade A, no knob)"}
READ_SRC = {"a": {"fvg_entry": "corpus: YAML 'The displacing leg must leave a fair value gap; that gap is then the entry'",
                  "lower_high": "corpus: YAML 'Downtrend: mark the successive lower highs. A shift occurs when one of them is broken WITH displacement'"},
            "b": {"stop_raid": "corpus: YAML 'A stop raid occurs first: price sweeps that swing' (later canon _94CPMjWi9E)",
                  "discount_entry": "corpus: YAML 'After the shift, mark the displacement range and take the entry only in its discount (long)'"}}

if __name__ == "__main__":
    rd = sys.argv[1]
    detect = make_detect(rd)
    ev = cl.cache_frame(f"{CID}_{rd}_{TF}", lambda: detect(cl.load_m1()))
    print(rd, len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="15D")
    print("probe", probe["passed"])
    res = cl.trade_test(ev, max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p", "mde",
                                   "win_rate", "exposure_bars", "ties", "ctrl_overlap")})
    op = {"rules": RULES[rd], "params": {"tf": TF, "swing": "2/2", "wait": WAIT, "rr": RR, "max_hold": HOLD}}
    p = cl.write_result(CID, rd, res, operationalization=op, params_source={**SRC, **READ_SRC[rd]},
                        script=__file__, probe=probe,
                        notes={"a": "older-playlist reading (break of a lower high with an FVG; FVG entry)",
                               "b": "later-canon reading (stop raid then close through the swing; discount entry)"}[rd])
    print(p)
