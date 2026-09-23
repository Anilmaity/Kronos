"""delta-divergence-recency-limit (HolyAngelBruv, guest) -> UNTESTABLE.

The concept is about MARKET DELTA (aggressor buy volume minus aggressor sell volume,
read from a footprint) diverging from price, and rejecting divergences whose legs are
more than ~4 hours apart. The certified XAUUSD data carries only open/high/low/close
per M1 bar (columns: open, high, low, close) - no volume at all, let alone aggressor-
signed volume. OANDA spot gold is an OTC CFD quote stream with no exchange tape, so
delta cannot be reconstructed. Any OHLC 'delta proxy' (close-location value, up-bar
count) would be testing a different indicator than the one the concept names.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

m1 = cl.load_m1()
assert list(m1.columns) == ["open", "high", "low", "close"], m1.columns
p = cl.write_untestable(
    "delta-divergence-recency-limit",
    "Needs footprint / market-delta (aggressor-signed volume) data. The certified XAUUSD "
    "M1 file has only open/high/low/close (no volume column at all) and OANDA spot gold "
    "is an OTC quote stream with no exchange tape, so delta and its divergence from price "
    "cannot be computed; an OHLC proxy would test a different indicator. The speaker also "
    "states he does not really use delta himself.",
    script=__file__,
    notes="Checked: load_m1() columns == ['open','high','low','close'].")
print(p)
