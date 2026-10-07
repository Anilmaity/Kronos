"""update_20261007 / prop-firm-drawdown-sizing, reading u1007a: UNTESTABLE.

New claims only (prior reading untestable, kept): (live_01, ES-R3ByDYrY) a 2-mini ceiling on a
50k funded NQ/ES account; (live_04, 9H15ZZvaKPQ) on trailing / intraday-trailing drawdown
accounts risk a small slice of the drawdown ($100 of $1,500) and scale through more accounts.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("position-size / prop-account rules, not a market claim. (1) 'two minis on 50k funded "
          "account' ... 'you're you're just not profitable' (ES-R3ByDYrY; verbatim 'trade two more "
          "than a mini or two minis', so whether two is allowed is ambiguous; speaker unmarked, said "
          "as banter during an MNQ competition) is a contract ceiling on NQ/ES "
          "futures (instruments we lack) and a sizing cap; contract count rescales P&L uniformly and "
          "cannot change a book's control-adjusted R on XAUUSD. (2) 'when you have trailing or "
          "intraday trailing ... accounts, you need to risk less money ... risking less and using "
          "more accounts' (9H15ZZvaKPQ) is account arithmetic ($1,500 trailing drawdown, $100 vs $700 "
          "risk) that holds by construction and depends on the firm's trailing-drawdown mechanics and "
          "multi-account economics, none of which is in M1 XAUUSD mid OHLC. Its measurables "
          "(breach probability under trailing vs static drawdown at each risk size) are Monte Carlo "
          "properties of a given strategy's R stream under firm rules, not falsifiable claims about "
          "the instrument; no trade/gate/rate test on gold decides them.")

if __name__ == "__main__":
    p = cl.write_untestable("prop-firm-drawdown-sizing", REASON, reading="u1007a", script=__file__,
                            notes="Covers both new drafts (live_01 contract ceiling, speaker unclear; "
                                  "live_04 trailing-drawdown risk rule). Prior unlabelled reading untouched. "
                                  "Audited 2026-10-07 against vault notes: verdict unchanged; live_01 "
                                  "quote corrected to transcript wording (was a non-verbatim paraphrase).")
    print(p)
