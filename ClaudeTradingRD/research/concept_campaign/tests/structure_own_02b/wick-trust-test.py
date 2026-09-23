"""wick-trust-test — gate_test, two readings (contested: the HTF/LTF pairing).

Concept ("let the wick form, trade the body"; method_spec §3.6): an extreme of the
higher-timeframe candle is TRUSTED — and becomes the stop — when (1) it formed EARLY in the
HTF candle, (2) the reach into it was a SHALLOW opposing run, and (3) a lower-timeframe CISD
closed through the series that made it. If all three hold, trade the body from the extreme;
otherwise widen the stop or skip.

Baseline book (stated): every LTF CISD (phase-3 rung-0 config) whose protected swing IS the
current HTF candle's running extreme at the confirming close (i.e. the CISD confirms that
candle's wick — condition 3 is in the baseline). Decide at the CISD close, stop = the
extreme, 2R, 10 LTF bars.
Gate trusted = early AND shallow:
  early   : the M1 minute of the extreme sits in the first 25% of the HTF candle's period
            (threshold_fits time-axis default 0.25; the corpus's "not midway" ceiling is 0.5)
  shallow : opposing run (HTF open -> extreme) <= 0.30 x the PREVIOUS closed HTF candle's
            range (threshold_fits range-cut default 0.30; the current candle's final range is
            not knowable live, so the prior candle's range is the declared denominator)
claim '+': trusted-wick trades beat untrusted ones, control-adjusted.
Readings (the YAML: 'the supporting timeframe varies ... without a stated pairing rule'):
  (a) 4H candle / 15m CISD   (b) 1D candle / 1h CISD
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ns, empty, cisd_frame, M1, PHASE3_SRC  # noqa: E402

CID = "wick-trust-test"
EARLY = 0.25
SHALLOW = 0.30
RR = 2.0
READ = {"a": ("4h", "15min", "150min"), "b": ("1D", "1h", "10h")}
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "trusted", "early", "shallow"]


def make_detect(htf: str, ltf: str):
    def detect(m1: pd.DataFrame) -> pd.DataFrame:
        hb = cl.build_bars(m1, htf)
        lb = cl.build_bars(m1, ltf)
        if len(hb) < 3 or len(lb) < 20:
            return empty(COLS)
        ev = cisd_frame(lb)
        if ev.empty:
            return empty(COLS)
        hst, hct = ns(hb.index), ns(hb["close_time"])
        ho, hh, hl = (hb[k].to_numpy(float) for k in ("open", "high", "low"))
        lst = ns(lb.index)
        m = M1(m1)
        rows = []
        for r in ev.itertuples(index=False):
            cp, xp = int(r.conf_pos), int(r.ext_pos)
            k = int(np.searchsorted(hst, lst[cp], "right") - 1)
            if k < 1 or lst[xp] < hst[k] or lst[cp] >= hct[k]:
                continue                               # extreme and CISD inside one HTF candle
            tconf = ns(pd.DatetimeIndex([r.conf_close_time]))[0]
            a = int(np.searchsorted(m.t, hst[k], "left"))
            z = int(np.searchsorted(m.t, tconf, "left"))
            if z <= a:
                continue
            bull = r.sgn == 1
            seg = m.l[a:z] if bull else m.h[a:z]
            j = int(np.argmin(seg) if bull else np.argmax(seg))
            ext = seg[j]
            if abs(ext - r.protected_swing) > 1e-9:
                continue                               # CISD extreme is not the candle's wick
            share = (m.t[a + j] - hst[k]) / (hct[k] - hst[k])
            opp = (ho[k] - ext) if bull else (ext - ho[k])
            prng = hh[k - 1] - hl[k - 1]
            if not (prng > 0) or opp < 0:
                continue
            early = bool(share <= EARLY)
            shallow = bool(opp <= SHALLOW * prng)
            rows.append((tconf, int(r.sgn), float(r.protected_swing), early and shallow, early, shallow))
        if not rows:
            return empty(COLS)
        out = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "trusted", "early", "shallow"])
        t = pd.DatetimeIndex(pd.to_datetime(out["t"].to_numpy(np.int64), utc=True))
        out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": out["direction"].to_numpy(),
                            "stop_px": out["stop_px"].to_numpy(), "rr": RR,
                            "trusted": out["trusted"].to_numpy(bool), "early": out["early"].to_numpy(bool),
                            "shallow": out["shallow"].to_numpy(bool)})
        return out.sort_values("decision_time", kind="stable").reset_index(drop=True)[COLS]
    return detect


SRC = {"htf_ltf": "corpus: YAML examples 'hourly under a daily and ... 15-minute under the 4-hour' (method_spec §1.2 pairing)",
       "cisd": PHASE3_SRC, "rr": PHASE3_SRC, "max_hold": PHASE3_SRC,
       "early": "threshold_fits: time_share_to_extreme default 0.25 (ceiling 0.5 = 'not midway', grade B)",
       "shallow": "threshold_fits: opposing_run/range default 0.30; denominator = previous closed HTF candle range, declared-before-run (the live candle's range is unknowable at the decision)",
       "grid4h": "session_window_fit: forex grid for gold"}

if __name__ == "__main__":
    rd = sys.argv[1]
    htf, ltf, hold = READ[rd]
    detect = make_detect(htf, ltf)
    ev = cl.cache_frame(f"{CID}_{htf}_{ltf}", lambda: detect(cl.load_m1()))
    print(rd, len(ev), ev[["trusted", "early", "shallow"]].mean().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D" if htf != "1D" else "30D")
    print("probe", probe["passed"])
    res = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold=hold)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap")})
    op = {"rules": [
        f"{htf} candles (forex 4h grid / NY 18:00 day); {ltf} CISD = phase-3 rung 0 (series_open, 2/2, max_wait 3)",
        "keep CISDs whose swing-extreme bar and confirming bar lie in the same HTF candle and whose protected swing "
        "equals that candle's running extreme (M1) at the confirming close",
        "decide at the CISD close; enter next M1 open; stop = the extreme; target 2R; hold 10 LTF bars",
        f"gate trusted = early (M1 minute of the extreme <= {EARLY} of the HTF period) AND shallow "
        f"(HTF open -> extreme <= {SHALLOW} x previous HTF candle range)"],
        "params": {"htf": htf, "ltf": ltf, "early": EARLY, "shallow": SHALLOW, "rr": RR, "max_hold": hold,
                   "cisd": "series_open 2/2 max_wait 3", "grid4h": "forex"}}
    src = {**SRC, "htf": SRC["htf_ltf"], "ltf": SRC["htf_ltf"]}
    p = cl.write_result(CID, rd, res, operationalization=op, params_source=src, script=__file__, probe=probe,
                        notes=f"gate firing rate {ev['trusted'].mean():.3f} (early {ev['early'].mean():.3f}, "
                              f"shallow {ev['shallow'].mean():.3f}) on {len(ev)} wick-confirming CISDs")
    print(p)
