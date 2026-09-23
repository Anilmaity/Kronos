"""risk_own_02a / idea-vs-executable-setup — gate_test on the 15m rung-0 CISD book.

Claim (+): a setup whose invalidation is a trustworthy single opposing swing beats one
whose stop would sit behind a pair of near-equal highs/lows ("the swing high it would
risk against is a pair of near-equal highs with no SMT ... no opposing candle he trusts
as an invalidation and therefore no trade").
  stop level     the book's protected swing (the 2/2 swing the CISD turned on)
  equal pair     another 2/2 swing of the same side formed in the 20 15m bars before it,
                 whose extreme is within 0.10 x ATR(14, 15m, as of the protected bar) of it
  gate (kept)    no equal pair -> an executable setup; complement = 'idea only' entries.
SMT against gold's correlated set (gold-in-EUR / gold-in-GBP) cannot be computed: only
XAUUSD is in the certified data, so every equal pair is treated as SMT-less. The 'no model
printed on the daily chart' clause is the daily-bias gate already tested in phase 3.
Params declared before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_02a")
from _common import *   # noqa

EQ_WIN = 20
EQ_TOL_ATR = 0.10
ATR_N = 14


def detect(m1):
    ev, raw, b = cisd_book(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev.empty:
        return ev[cols].assign(trusted_stop=pd.Series(dtype=bool))
    h, l_, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l_, np.abs(h - pc), np.abs(l_ - pc)], axis=1)
    atr = pd.Series(tr).rolling(ATR_N, min_periods=ATR_N).mean().to_numpy()
    sw = swing_points(b[["open", "high", "low", "close"]], 2, 2)
    sh, sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    eq = np.zeros(len(ev), bool)
    ok = np.ones(len(ev), bool)
    for r, (pos, d) in enumerate(zip(ev["ext_pos"].to_numpy(), ev["direction"].to_numpy())):
        a = atr[pos]
        if not np.isfinite(a) or pos < 1:
            ok[r] = False
            continue
        lo_ = max(0, pos - EQ_WIN)
        if d == 1:      # long: stop below a swing low
            prev = np.flatnonzero(sl[lo_:pos]) + lo_
            eq[r] = (np.abs(l_[prev] - l_[pos]) <= EQ_TOL_ATR * a).any()
        else:
            prev = np.flatnonzero(sh[lo_:pos]) + lo_
            eq[r] = (np.abs(h[prev] - h[pos]) <= EQ_TOL_ATR * a).any()
    out = ev[cols][ok].reset_index(drop=True)
    out["trusted_stop"] = ~eq[ok]
    return out


if __name__ == "__main__":
    ev = cl.cache_frame(f"idea_{TF}_w{EQ_WIN}_tol{EQ_TOL_ATR}_atr{ATR_N}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["trusted_stop"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "trusted_stop", mask_available_at="decision_time", max_hold=HOLD, claim="+")
    show(res)
    params = {**BASE_PARAMS, "equal_window_15m_bars": EQ_WIN, "equal_tol_atr": EQ_TOL_ATR,
              "atr_n": ATR_N, "smt": "not computable (no correlated series); all equal pairs treated as SMT-less"}
    src = {**BASE_SRC,
           "equal_window_15m_bars": "declared-before-run: a pair of highs within the same 5-hour swing leg",
           "equal_tol_atr": "declared-before-run: method_spec 'Relatively equal highs/lows ... Tolerance is never given [GAP]'",
           "atr_n": "declared-before-run: conventional 14",
           "smt": "declared-before-run: certified data holds XAUUSD only"}
    op = {"rules": [BASE_RULE,
                    "stop level = protected swing of the CISD",
                    "untrusted = another same-side 2/2 swing in the 20 bars before it within 0.10 x ATR(14)",
                    "gate = trusted (no equal pair); claim +: trusted-invalidation setups beat equal-highs/lows ones"],
          "params": params}
    p = cl.write_result("idea-vs-executable-setup", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes=("Tests the OHLC-decidable half (equal highs/lows as an untrusted "
                               "invalidation). The SMT rescue clause cannot be computed without "
                               "gold-in-EUR/GBP series, so the complement mixes SMT-present and "
                               "SMT-absent pairs; this attenuates rather than fabricates an effect. "
                               "mask_available_at = decision time (all swings closed by then)."))
    print("wrote", p)
