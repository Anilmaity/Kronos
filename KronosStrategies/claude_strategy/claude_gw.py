#!/usr/bin/env python3
"""claude-gw — SSH forced command for the Claude Strategy key.

Installed on the box as /home/ubuntu/bin/claude-gw and bound to reaper's key in
~/.ssh/authorized_keys with command="/home/ubuntu/bin/claude-gw",no-pty,... so
that key can run claude_trade.py subcommands and nothing else. argv is exec'd
without a shell; every call is logged to ~/claude-gw.log.
Spec: KronosStrategies/docs/superpowers/specs/2026-10-06-claude-strategy-design.md §3.3
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys

CONTAINER = os.getenv("CLAUDE_GW_CONTAINER", "kronos-s93_fvg_scalp-1")
LOG = os.path.expanduser("~/claude-gw.log")

_NUM = re.compile(r"^\d{1,6}(\.\d{1,3})?$")
_TFS = re.compile(r"^(1m|5m|15m|1h|4h|1d)(,(1m|5m|15m|1h|4h|1d))*$")
_FLAGS = {
    "status": {},
    "market": {"--tf": _TFS.match,
               "--bars": lambda v: v.isdigit() and 1 <= int(v) <= 300},
    "open": {"--side": lambda v: v in ("BUY", "SELL"), "--sl": _NUM.match, "--tp": _NUM.match},
    "close": {},
}
_NEEDS_WHY = {"open", "close"}
_REQUIRED = {"open": {"--side", "--sl", "--tp"}}


def parse(raw: str) -> list[str]:
    """Validated argv for claude_trade.py, or ValueError. Everything after
    ' --why ' is the free-text reason (the local shell has already stripped
    its quotes, so it arrives as loose words)."""
    head, sep, why = raw.partition(" --why ")
    argv = head.split()
    if not argv or argv[0] not in _FLAGS:
        raise ValueError(f"unknown subcommand: {head[:40]!r}")
    cmd, rest = argv[0], argv[1:]
    allowed = _FLAGS[cmd]
    if len(rest) % 2:
        raise ValueError("flags must be --name value pairs")
    seen = set()
    for flag, val in zip(rest[::2], rest[1::2]):
        check = allowed.get(flag)
        if check is None or flag in seen or not check(val):
            raise ValueError(f"bad argument: {flag} {val!r}")
        seen.add(flag)
    missing = _REQUIRED.get(cmd, set()) - seen
    if missing:
        raise ValueError(f"missing {sorted(missing)}")
    if cmd in _NEEDS_WHY:
        why = why.strip().strip("'\"").strip()
        if not sep or not why:
            raise ValueError("--why <reason> is required")
        if len(why) > 500 or any(c in why for c in "\n\r\x00"):
            raise ValueError("--why must be one line, at most 500 chars")
        argv += ["--why", why]
    elif sep:
        raise ValueError(f"{cmd} takes no --why")
    return argv


def docker_argv(argv: list[str]) -> list[str]:
    return ["docker", "exec", CONTAINER, "python", "claude_trade.py", *argv]


def _log(line: str) -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG, "a") as f:
        f.write(f"{stamp} {line}\n")


def main() -> int:
    raw = os.environ.get("SSH_ORIGINAL_COMMAND", "").strip()
    try:
        argv = parse(raw)
    except ValueError as e:
        _log(f"DENY  {raw[:600]!r} — {e}")
        print(json.dumps({"ok": False, "error": f"claude-gw: {e}"}))
        return 1
    _log(f"ALLOW {raw[:600]!r}")
    os.execvp("docker", docker_argv(argv))


if __name__ == "__main__":
    sys.exit(main())
