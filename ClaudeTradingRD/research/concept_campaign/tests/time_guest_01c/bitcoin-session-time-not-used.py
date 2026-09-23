"""bitcoin-session-time-not-used (guest: AM Trades) -> UNTESTABLE.

The concept is an instrument-specific rule: on Bitcoin (a 24/7 instrument) do not
apply kill-zone/session filters; trade it off the 1H/1D. Its only measurables are
"expectancy of Bitcoin setups inside vs outside the index kill zones" and "Bitcoin
realised volatility by hour". concept_lab serves only the certified XAUUSD M1 span
(load_m1), and gold is not a 24/7 instrument (daily 17:00-18:00 NY halt, weekend
close) — the very property the guest gives as his reason. Re-running a kill-zone gate
on gold would test a different claim (gold kill zones are already covered by the
killzone concepts), not this one.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("needs data we lack: the rule is stated only for Bitcoin, a 24/7 instrument "
          "('i don't gage time as important on bitcoin', CrUfTskOveo). The harness serves "
          "only certified XAUUSD M1, which halts daily and at weekends — the property the "
          "guest cites as his reason — so no BTC setup book or BTC hour-of-day volatility "
          "can be measured; transplanting the rule to gold would test a different claim.")

if __name__ == "__main__":
    p = cl.write_untestable("bitcoin-session-time-not-used", REASON, script=__file__,
                            notes="Gold kill-zone gates are tested under the killzone / "
                                  "entry-time-window concepts; this guest rule is BTC-only.")
    print(p)
