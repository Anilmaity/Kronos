"""house-money-capital-structure (guest: Trader Kane) - UNTESTABLE.

A capital-structure rule: deposit only what you can lose, never top up, withdraw the
initial once the account has grown, then size up on the remaining "house money". Every
element is account accounting or position-size arithmetic applied to the SAME trades
("not different trades, the same model at larger size"); its claimed benefit is purely
psychological (sizing without emotional interference), which the guest himself
acknowledges is framing, not an accounting fact. Nothing in it selects, times or exits a
trade, so there is no OHLC-decidable claim; the withdrawal trigger and the post-withdrawal
size multiple are also unquantified in the transcript.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402

if __name__ == "__main__":
    p = cl.write_untestable(
        "house-money-capital-structure",
        "pure capital-structure / sizing arithmetic with a psychological rationale: "
        "deposit sizing, no top-ups, withdrawing the initial and sizing up on the "
        "remainder change neither which trades are taken nor how they exit (same model, "
        "larger size), so no OHLC outcome can confirm or refute it; the withdrawal "
        "trigger and size-up multiple are also unstated",
        script=__file__)
    print(p)
