"""Put the Telegram_Bot package dir on sys.path so its flat-module imports
(`import metaapi_orders`, `import live_trader`, …) resolve when pytest is run
from the repo root or anywhere else."""
import sys
from pathlib import Path

_BOT_DIR = Path(__file__).resolve().parent.parent
if str(_BOT_DIR) not in sys.path:
    sys.path.insert(0, str(_BOT_DIR))

import pytest


@pytest.fixture(autouse=True)
def _one_leg_per_tp(monkeypatch):
    """Most tests exercise the order/close mechanics with one leg per posted TP
    and the stop-to-entry breakeven. The live defaults (5 legs, partial
    breakeven) have their own tests in test_five_legs_and_breakeven.py."""
    import live_trader as lt
    monkeypatch.setattr(lt, "LEG_COUNT", 0)
    monkeypatch.setattr(lt, "BE_KEEP_LEGS", 0)
