"""Claude Strategy executor — CLI surface (the DB/broker paths are verified live in PAPER)."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "strategies"))

import pytest

import claude_trade as ct


def test_parser_accepts_the_four_subcommands():
    p = ct.build_parser()
    assert p.parse_args(["status"]).cmd == "status"
    a = p.parse_args(["market", "--tf", "5m,1h", "--bars", "50"])
    assert (a.tf, a.bars) == ("5m,1h", 50)
    a = p.parse_args(["open", "--side", "SELL", "--sl", "4135", "--tp", "4120", "--why", "x y"])
    assert (a.side, a.sl, a.tp, a.why) == ("SELL", 4135.0, 4120.0, "x y")
    assert p.parse_args(["close", "--why", "CHoCH against"]).cmd == "close"


@pytest.mark.parametrize("argv", [
    ["open", "--side", "HOLD", "--sl", "1", "--tp", "2", "--why", "x"],
    ["open", "--side", "BUY", "--tp", "2", "--why", "x"],          # no SL
    ["market", "--tf", "2m"],
    ["market", "--bars", "301"],
    ["close"],                                                     # no reason
])
def test_parser_rejects_bad_input(argv):
    with pytest.raises(SystemExit):
        ct.build_parser().parse_args(argv)


def test_variation_tag_is_registered():
    src = open(os.path.join(os.path.dirname(__file__), "..", "strategies", "strategy",
                            "entry_manager.py")).read()
    assert re.search(r'"claude_strategy":\s+"Claude Strategy"', src)
