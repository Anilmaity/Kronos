"""relative-strength-asset-selection — update_20261007, reading u1007a (new claim only).

New testable claim (shorts_01, HIIxLzC1atE): between correlated assets, on the candle that
validates the CISD, the asset whose candle closes through the CISD level is the weaker one (bearish
case) and the one that cannot close through it is stronger; applied to gold as XAUUSD vs XAUGBP.
Testable implication with gold as the only tradeable asset: a gold CISD where XAUGBP FAILS to close
through its own corresponding level on the same 1h candle (gold uniquely through = gold is the
weaker asset for a short / stronger for a long, i.e. the right asset) beats a gold CISD where XAUGBP
also closes through. claim '+'.

Not tested (data we lack): the ES/NQ/YM triad rules (stand aside when out of order, trade ES when
NQ is through the low and YM reversed, ES leads ~1 day in 10). The SMT higher-low reading is already
in the library entry (prior readings a/b, vs silver), so it is not re-run here.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_04b")
from pathlib import Path
import numpy as np
import pandas as pd
from _common import cl, cisd_frame, HOLD, CISD, RR

TF = "1h"
H1 = pd.Timedelta(hours=1)
GBP_FILE = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02b/data/xau_gbp_h1.parquet")
_RAW = {}


def xau_gbp():
    if "g" not in _RAW:
        d = pd.read_parquet(GBP_FILE)[["open", "high", "low", "close"]].astype("float64")
        d.index = pd.DatetimeIndex(d.index).tz_convert("UTC")
        _RAW["g"] = d.sort_index()
    return _RAW["g"]


def detect(m1):
    b, ev, out = cisd_frame(m1, TF)
    cutoff = m1.index[-1] + pd.Timedelta(minutes=1)
    x = xau_gbp()
    x = x[x.index + H1 <= cutoff + H1]           # never beyond gold's own last bar
    xs = x.reindex(pd.DatetimeIndex(ev["series_start"]))
    xc = x.reindex(pd.DatetimeIndex(ev["confirm_time"]))
    lvl = xs["open"].to_numpy(float)              # series_open rule applied to XAUGBP's same bars
    cls = xc["close"].to_numpy(float)
    ok = np.isfinite(lvl) & np.isfinite(cls)
    d = out["direction"].to_numpy()
    gbp_through = np.where(d == 1, cls > lvl, cls < lvl)
    out["gold_unique_close"] = np.where(ok, ~gbp_through, False).astype(bool)
    return out[ok].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"rsas_u1007a_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev), float(ev["gold_unique_close"].mean()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "gold_unique_close", mask_available_at="decision_time", max_hold=HOLD[TF], claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
                                   "exposure_bars", "ties", "ctrl_overlap")})
    src = {k: "phase3: meta/conjunction_preregistration.md locked rung-0 config" for k in
           ("tf", "level_rule", "left", "right", "max_wait", "min_series", "rr", "max_hold")}
    src.update({
        "correlate": "corpus: HIIxLzC1atE 'there is weakness in gold GBP, while gold is a slight bit stronger' (XAUUSD vs gold-GBP); OANDA XAU_GBP H1 mid, liquidity_own_02b/data",
        "discriminator": "corpus: HIIxLzC1atE 'this candle closes below, validating this change in the state of delivery ... on the right here, we can't close below that level'",
        "correlate_level": "declared-before-run: XAUGBP's level = open of the same series-start 1h bar as gold's series_open CISD level (the corpus compares the same candle on both charts)",
        "closure_tf": "declared-before-run: 1h, the rung-0 execution timeframe; the Short does not state the timeframe (yaml ambiguity)",
    })
    params = {"tf": TF, **CISD, "rr": RR, "max_hold": HOLD[TF], "correlate": "XAU_GBP H1",
              "discriminator": "XAUGBP fails to close through its level on gold's CISD confirming candle",
              "correlate_level": "XAUGBP open at gold series_start bar", "closure_tf": "1h"}
    op = {"rules": [
        "baseline: gold 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming bar's close, enter next M1 open; stop at the protected swing, 2R, 10h wall clock",
        "correlate: XAUGBP H1 (OANDA mid) read at gold's series-start bar (open = its CISD level) and gold's confirming bar (close); events lacking either bar dropped",
        "gate: on the confirming candle gold closes through its CISD level (by construction) while XAUGBP does NOT close through its own level -> gold is the weaker (short) / stronger (long) asset, the right one to trade",
        "claim: gated gold CISDs beat those where XAUGBP also closed through (control-adjusted R)"],
        "params": params}
    path = cl.write_result("relative-strength-asset-selection", "u1007a", res, operationalization=op,
                           params_source=src, script=__file__, probe=probe,
                           notes=f"gate firing rate {float(ev['gold_unique_close'].mean()):.3f} of {len(ev)}. Only the XAUUSD-vs-XAUGBP closure claim is testable; "
                                 "the ES/NQ/YM triad rules (stand-aside, trade-ES catch-up, ES leads ~1/10 days) need index data we lack.")
    print("wrote", path)
