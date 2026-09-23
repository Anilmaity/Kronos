"""concept_lab — the shared, read-only harness for the 471-concept XAUUSD campaign.

    import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
    import concept_lab as cl

See README.md in this directory. Everything statistical is decided in `rules.py`
(LOCKED) and every test type returns the same result shape, which
`write_result` validates and persists.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PY = Path(__file__).resolve().parents[1]           # research/python
if str(_PY) not in sys.path:
    sys.path.insert(0, str(_PY))

from . import rules                                                  # noqa: E402
from .rules import (verdict, RULES_VERSION, SPLIT_DATE, EDGE, NEGATIVE,   # noqa: E402,F401
                    NULL, UNDERPOWERED, UNTESTABLE)
from .data import (load_m1, bars, build_bars, asof, cache_frame, span,     # noqa: E402,F401
                   build_fingerprint,
                   normalize_tf, tf_delta, trading_day, session_date, close_time_of,
                   CAMPAIGN_DIR, CACHE_DIR, RESULTS_DIR)
from .sessions import (to_ny, ny_minute_of_day, in_window, KILLZONES,      # noqa: E402,F401
                       SESSION_WINDOWS, window_hilo, prior_hilo, open_at,
                       running_hilo)
from .lookahead import (LookaheadError, assert_no_lookahead,               # noqa: E402,F401
                        probe_lookahead, frame_fingerprint)
from .engine import (get_market, resolve_trades, sample_times, touch)      # noqa: E402,F401
from .tests_api import trade_test, gate_test, rate_test                    # noqa: E402,F401
from .results import (write_result, write_untestable, load_results,        # noqa: E402,F401
                      adjust_campaign, validate_result, SCHEMA_FIELDS, load_ledger)

__version__ = "1.1.0"
HARNESS_VERSION = f"concept_lab-{__version__}"
