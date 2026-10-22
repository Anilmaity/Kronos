"""A failed region lookup must not pin the account to new-york: it is retried
after REGION_RETRY_SEC and the real region is kept once the lookup succeeds."""
import metaapi_orders as mx


class _Resp:
    def __init__(self, region):
        self._region = region

    def raise_for_status(self):
        if self._region is None:
            raise mx.requests.HTTPError("504")

    def json(self):
        return {"region": self._region}


def test_failed_lookup_is_retried_then_cached(monkeypatch):
    answers = [None, "london"]
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return _Resp(answers[len(calls) - 1])

    clock = [1000.0]
    monkeypatch.setattr(mx.requests, "get", fake_get)
    monkeypatch.setattr(mx.time, "monotonic", lambda: clock[0])
    c = mx.MetaApiClient("tok", "acc", label="t")

    assert "new-york" in c._resolve_trading_url()     # lookup fails → fallback
    assert "new-york" in c._resolve_trading_url()     # within the retry window: no new lookup
    assert len(calls) == 1

    clock[0] += mx.REGION_RETRY_SEC + 1
    assert "london" in c._resolve_trading_url()       # retried → real region
    clock[0] += 10 * mx.REGION_RETRY_SEC
    assert "london" in c._resolve_trading_url()       # kept, no more lookups
    assert len(calls) == 2
