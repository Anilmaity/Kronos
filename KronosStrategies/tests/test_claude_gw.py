"""claude-gw — the SSH forced command that is the reaper session's only way onto the box."""
import importlib.util
import os

import pytest

_spec = importlib.util.spec_from_file_location(
    "claude_gw", os.path.join(os.path.dirname(__file__), "..", "claude_strategy", "claude_gw.py"))
gw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gw)


@pytest.mark.parametrize("raw,want", [
    ("status", ["status"]),
    ("market", ["market"]),
    ("market --tf 5m,15m,1h --bars 120", ["market", "--tf", "5m,15m,1h", "--bars", "120"]),
    ("open --side SELL --sl 4135.5 --tp 4120 --why OB rejection",
     ["open", "--side", "SELL", "--sl", "4135.5", "--tp", "4120", "--why", "OB rejection"]),
    ("close --why CHoCH against the trade", ["close", "--why", "CHoCH against the trade"]),
])
def test_allowed(raw, want):
    assert gw.parse(raw) == want


def test_why_takes_rest_of_line():
    # The local shell strips the quotes, so the box sees the words unquoted.
    assert gw.parse("open --side BUY --sl 4125 --tp 4140 --why M15 FVG retest")[-1] == "M15 FVG retest"
    assert gw.parse("close --why 'quoted reason'")[-1] == "quoted reason"


@pytest.mark.parametrize("raw", [
    "", "ls", "status; rm -rf /", "status && id", "market --tf $(id)",
    "open --side `id` --sl 1 --tp 2 --why x",
    "market --bars 301", "market --tf 2m", "market --tf 5m --tf 1h",
    "open --side BUY --sl 1 --tp 2",                 # no reason
    "open --sl 4125 --tp 4140 --why x",              # no side
    "open --side BUY --sl 41e3 --tp 4140 --why x",   # not a plain number
    "close", "status --why x", "open --side BUY --sl 1 --tp 2 --qty 9 --why x",
])
def test_rejected(raw):
    with pytest.raises(ValueError):
        gw.parse(raw)


def test_injection_is_inert():
    # Metacharacters inside the reason are just text: argv is exec'd without a shell.
    argv = gw.parse("close --why x; rm -rf / $(id)")
    assert argv == ["close", "--why", "x; rm -rf / $(id)"]
    assert gw.docker_argv(argv)[:3] == ["docker", "exec", gw.CONTAINER]


def test_why_length_cap():
    with pytest.raises(ValueError):
        gw.parse("close --why " + "x" * 501)
