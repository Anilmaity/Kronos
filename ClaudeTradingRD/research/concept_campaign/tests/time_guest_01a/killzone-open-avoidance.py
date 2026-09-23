"""killzone-open-avoidance (guest: Day Trading Rauf, qFtfD09Vv3E).

"I would never trade at the beginning of a Kill Zone ... if you start to use 7:30
opening price or 8:30 opening price you can see quite clearly where the market is ...
[at the start] it's doing the opposite of what it is actually going to do."

Two claims in the one concept, tested as two readings (declared before any run):

  a  AVOIDANCE (gate_test, claim '+'): baseline book = bare 15m CISD (phase-3 locked
     config) restricted to decisions inside a forex kill zone (killzones.yaml: Asia
     20-00, London 02-05, NY AM 07-10, London Close 10-12 NY). Gate = the decision is
     NOT in the first 30 minutes of its kill zone. 'Beginning' = 30 minutes because his
     own remedy is the 07:30 opening price, 30 minutes into the 07:00 window.
     Complement = decisions at KZ start + 0 / + 15 min.

  b  ENTICE / REVERSAL (rate_test, claim '+'): the 07:00-07:30 NY move is opposite
     the rest of the day's direction. Predictor at 07:30 = sign(07:29 close - 07:00
     open); outcome = sign(16:59 close - 07:30 open) is the opposite sign. Null = the
     same statistic at matched random moments (+/-30d, same minute grid): a 30-M1-bar
     move vs the following move over the same number of M1 bars.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import PHASE3_CISD, cl, detect_cisd, np, pd, show  # noqa: E402

CID = "killzone-open-avoidance"
KZS = ("fx_asia", "fx_london", "fx_ny_am", "fx_london_close")
BEGIN_MIN = 30
TF = "15min"
MAX_HOLD = "150min"
WIN_START, WIN_END = "07:00", "07:30"
DAY_END = "17:00"
MIN_COVER = 20


def _kz_flags(t: pd.DatetimeIndex):
    mod = cl.ny_minute_of_day(t)
    in_kz = np.zeros(len(t), bool)
    at_begin = np.zeros(len(t), bool)
    for k in KZS:
        a, b = cl.KILLZONES[k]
        in_kz |= cl.in_window(t, a, b)
        h, m = a.split(":")
        s = int(h) * 60 + int(m)
        at_begin |= (((mod - s) % 1440) < BEGIN_MIN)
    return in_kz, at_begin


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    ev = detect_cisd(m1, TF)
    if ev.empty:
        return ev.assign(later_in_kz=pd.Series(dtype=bool))
    t = pd.DatetimeIndex(ev["decision_time"])
    in_kz, at_begin = _kz_flags(t)
    ev = ev[in_kz].reset_index(drop=True)
    ev["later_in_kz"] = ~at_begin[in_kz]
    return ev


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "first_move"]
    t = pd.DatetimeIndex(m1.index)
    mod = cl.ny_minute_of_day(t)
    sel = cl.in_window(t, WIN_START, WIN_END)
    if not sel.any():
        return pd.DataFrame(columns=cols)
    sub = m1.loc[sel]
    ny = t[sel].tz_convert("America/New_York")
    day = ny.normalize()
    g = pd.DataFrame({"o": sub["open"].to_numpy(), "c": sub["close"].to_numpy(),
                      "mod": mod[sel]}, index=day)
    agg = g.groupby(level=0).agg(o=("o", "first"), c=("c", "last"), n=("o", "size"),
                                 last=("mod", "max"))
    agg = agg[agg["n"] >= MIN_COVER]
    dec = (agg.index + pd.Timedelta("7h30min")).tz_convert("UTC")
    # the window must be over in the input data (a truncated day is not a decision)
    last_t = t[-1] + pd.Timedelta("1min")
    move = np.sign(agg["c"].to_numpy() - agg["o"].to_numpy())
    out = pd.DataFrame({"decision_time": dec, "available_at": dec, "first_move": move})
    out = out[(out["decision_time"] <= last_t) & (out["first_move"] != 0)]
    return out.reset_index(drop=True)


def run_a():
    ev = cl.cache_frame(f"{CID}_a_cisd15_v1", lambda: detect_a(cl.load_m1()))
    print("a: n", len(ev), "later share", ev["later_in_kz"].mean())
    probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
    res = cl.gate_test(ev, "later_in_kz", mask_available_at="decision_time", max_hold=MAX_HOLD,
                       claim="+")
    show(res)
    op = {"rules": [
        "baseline: bare 15m CISD (series_open level, 2/2 swings, max_wait 3), decide at the confirming "
        "15m close, enter next M1 open, stop at the protected swing, 2R, hold 150 min",
        "keep only decisions inside a forex kill zone: Asia 20:00-00:00, London 02:00-05:00, NY AM 07:00-10:00, "
        "London Close 10:00-12:00 NY",
        "gate (pass) = decision NOT in the first 30 minutes of its kill zone; complement = decision at "
        "KZ start or start+15 min (entries on the kill zone's first candles)",
        "claim '+': entries later in the kill zone beat entries at its beginning"],
        "params": {"tf": TF, "max_hold": MAX_HOLD, "killzones": list(KZS), "begin_minutes": BEGIN_MIN,
                   "level_rule": "series_open", "swing": "2/2", "max_wait": 3, "rr": 2.0}}
    src = {"tf": "corpus: concept timeframes.ltf lists 15m (1H/15m/5m)",
           "max_hold": PHASE3_CISD, "level_rule": PHASE3_CISD, "swing": PHASE3_CISD,
           "max_wait": PHASE3_CISD, "rr": PHASE3_CISD,
           "killzones": "session_window_fit: concepts/time/killzones.yaml forex windows (cl.KILLZONES fx_*)",
           "begin_minutes": "corpus: qFtfD09Vv3E 'if you start to use 7 30 opening price' (remedy 30 min into the 07:00 window)"}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="Gold, not indices. Rauf states the rule generally ('a Kill Zone') "
                        "with the forex 07:00-10:00 window as his example, so all four forex kill zones are pooled.")
    print("wrote", p)


def run_b():
    m1 = cl.load_m1()
    mkt = cl.get_market()
    pr = cl.cache_frame(f"{CID}_b_first30_v1", lambda: detect_b(m1))
    probe = cl.probe_lookahead(detect_b, pr, lookback="10D")
    t = pd.DatetimeIndex(pr["decision_time"])
    N = len(mkt.tn)
    i0 = mkt.pos_at_or_after(t)
    ny = t.tz_convert("America/New_York").normalize()
    endt = (ny + pd.Timedelta("17h")).tz_convert("UTC")
    i1 = mkt.pos_at_or_after(endt)          # exclusive: last bar used = i1-1 (16:59)
    ok = (i0 < N) & (i1 - i0 >= 60)
    hb = (i1 - i0).astype(np.int64)
    first = pr["first_move"].to_numpy(float)

    def outcome(i_start, nb, move):
        i_start = np.asarray(i_start); nb = np.asarray(nb)
        j = np.clip(i_start + nb - 1, 0, N - 1)
        fwd = np.sign(mkt.c[j] - mkt.o[np.clip(i_start, 0, N - 1)])
        res = np.where((fwd == 0) | (move == 0), np.nan, (fwd == -move).astype(float))
        return res

    obs = np.where(ok, outcome(i0, hb, first), np.nan)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        out = np.full(len(t), np.nan)
        good = ~tk.isna() & ok
        ik = mkt.pos_at_or_after(tk[good])
        valid = (ik >= 30) & (ik + hb[good] <= N)
        ik2 = np.where(valid, ik, 30)
        mv = np.sign(mkt.c[ik2 - 1] - mkt.o[ik2 - 30])
        r = outcome(ik2, hb[good], mv)
        r[~valid] = np.nan
        out[np.flatnonzero(good)] = r
        return out

    res = cl.rate_test(obs, t, available_at=pr["available_at"], null_fn=null_fn, claim="+",
                       predictors=pr)
    show(res)
    op = {"rules": [
        "each NY trading day: first_move = sign(close of the last M1 bar before 07:30 NY - open of the first "
        "M1 bar at/after 07:00 NY); needs >= 20 of 30 M1 bars; decide at 07:30 NY",
        "outcome = the move from the 07:30 open to the 16:59 close has the OPPOSITE sign (flat days dropped)",
        "null = at matched random moments (+/-30d, same minute grid): sign of the preceding 30 M1 bars vs the "
        "sign over the same number of following M1 bars as the real day",
        "claim '+': the kill zone's opening move reverses more often than a random 30-minute move"],
        "params": {"window": [WIN_START, WIN_END], "day_end": DAY_END, "min_cover": MIN_COVER}}
    src = {"window": "corpus: qFtfD09Vv3E '7am to 10am ... never trade at the beginning ... 7 30 opening price'",
           "day_end": "declared-before-run: the day's direction read to the 17:00 NY daily close (18:00 roll)",
           "min_cover": "declared-before-run: at least 2/3 of the window's M1 bars present"}
    p = cl.write_result(CID, "b", res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="Tests 'it's doing the opposite of what it is actually going to do' "
                        "on the forex 07:00 window he names. Gold, not indices.")
    print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        run_a()
    if "b" in which:
        run_b()
