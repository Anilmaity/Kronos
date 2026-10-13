"""Re-entry: a complete signal posted as a reply is a new trade.

7 Oct 2026: the VIP channel's "Gold buy now 4116 - 4112 / SL 4107" re-entry
never traded — it arrived as a reply, and replies only ever went to the
management path. A reply that parses as a full signal (SL + TPs) now reaches
handle_new_signal, whose no-pyramiding guard decides whether anything is live.
A bare "re entry" with no levels is never traded.
"""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import live_trader as lt

SIGNAL = """Gold buy now 4116 - 4112

SL: 4107

TP: 4118
TP: 4120
TP: 4122
TP: 4124
TP: 4126
TP: open"""


def _msg(text, reply_to=None, msg_id=9001):
    return SimpleNamespace(
        id=msg_id, text=text, date=datetime.now(timezone.utc),
        reply_to=SimpleNamespace(reply_to_msg_id=reply_to) if reply_to else None)


@pytest.fixture
def new_signals(monkeypatch):
    seen = []

    async def fake_new(msg):
        seen.append(msg.id)

    async def no_mgmt(*a, **k):
        return None

    monkeypatch.setattr(lt, "handle_new_signal", fake_new)
    monkeypatch.setattr(lt, "apply_management", no_mgmt)
    return seen


@pytest.mark.parametrize("text", ["Re entry", "re-entry now", "REENTRY", "re entey buy"])
def test_reentry_regex_matches_variants(text):
    assert lt.REENTRY_RE.search(text)


@pytest.mark.parametrize("text", ["recent high", "represent", "rent", "set breakeven"])
def test_reentry_regex_ignores_other_words(text):
    assert not lt.REENTRY_RE.search(text)


def test_full_signal_as_reply_goes_to_new_signal(new_signals):
    asyncio.run(lt.handle_reply(_msg(SIGNAL, reply_to=7736)))
    assert new_signals == [9001]


def test_full_reentry_signal_as_reply_goes_to_new_signal(new_signals):
    asyncio.run(lt.handle_reply(_msg("Re entry\n" + SIGNAL, reply_to=7736)))
    assert new_signals == [9001]


@pytest.mark.parametrize("text", ["Re entry now", "re entry 4116", "Gold buy re entry now"])
def test_bare_reentry_reply_is_not_traded(new_signals, text):
    asyncio.run(lt.handle_reply(_msg(text, reply_to=7736)))
    assert new_signals == []


def test_reentry_bypasses_repost_guard(monkeypatch):
    """A re-entry repeats a zone on purpose; the repost guard must not eat it."""
    async def repost(*a):
        raise AssertionError("repost guard consulted for a re-entry")

    async def stop(**k):
        raise RuntimeError("reached account gate")

    monkeypatch.setattr(lt, "_is_repost", repost)
    monkeypatch.setattr(lt, "refresh_accounts", stop)
    monkeypatch.setattr(lt.db, "record_channel_signal", lambda *a: None)
    with pytest.raises(RuntimeError, match="account gate"):
        asyncio.run(lt.handle_new_signal(_msg("Re entry\n" + SIGNAL)))
