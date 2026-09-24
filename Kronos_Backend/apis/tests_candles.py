"""Unit tests for the chart candles resolver's history paging (`before`)."""
from unittest import mock

from django.test import SimpleTestCase

from apis.schema.query import get_candles as gc


def _bars(start, n, step):
    return [(start + i * step, 1.0, 2.0, 0.5, 1.5) for i in range(n)]


class CandlesBeforeTests(SimpleTestCase):
    def setUp(self):
        gc._CACHE.clear()

    def _resolve(self, **kw):
        args = {"symbol": "XAU_USD", "interval": "1h", "limit": 3}
        args.update(kw)
        return gc.GetCandles().resolve_candles(None, **args)

    def test_latest_page_does_not_send_to(self):
        with mock.patch.object(gc, "_fetch_oanda", return_value=_bars(0, 5, 3600)) as f:
            out = self._resolve()
        f.assert_called_once_with("XAU_USD", "H1", 3, to=None)
        self.assertEqual([c.time for c in out], [7200, 10800, 14400])

    def test_before_pages_back_and_is_strict(self):
        # OANDA may include a candle stamped exactly at `to`; it must be dropped
        with mock.patch.object(gc, "_fetch_oanda", return_value=_bars(0, 5, 3600)) as f:
            out = self._resolve(before=14400)
        f.assert_called_once_with("XAU_USD", "H1", 3, to=14400)
        self.assertEqual([c.time for c in out], [3600, 7200, 10800])
        self.assertTrue(all(c.time < 14400 for c in out))

    def test_cache_is_keyed_by_before(self):
        with mock.patch.object(gc, "_fetch_oanda", return_value=_bars(0, 5, 3600)) as f:
            self._resolve()
            self._resolve(before=14400)
        self.assertEqual(f.call_count, 2)

    def test_folded_interval_drops_partial_leading_bucket(self):
        # 3m is folded from M1; a history page can start mid-bucket
        bars = _bars(60, 8, 60)  # 60..480: first 3m bucket (0..179) is missing its 00:00 bar
        with mock.patch.object(gc, "_fetch_oanda", return_value=bars):
            out = self._resolve(interval="3m", limit=10, before=540)
        self.assertEqual([c.time for c in out], [180, 360])

    def test_fetch_formats_to_as_rfc3339(self):
        resp = mock.Mock(json=lambda: {"candles": []}, raise_for_status=lambda: None)
        with mock.patch.object(gc._session, "get", return_value=resp) as g:
            gc._fetch_oanda("XAU_USD", "H1", 10, to=1790000000)
        self.assertEqual(g.call_args.kwargs["params"]["to"], "2026-09-21T14:13:20Z")
