"""volume-profile-ledge (guest: HolyAngelBruv) -> UNTESTABLE.

Every rule of the concept is defined on a VOLUME profile: a ledge is a price whose traded
volume protrudes beyond its neighbours (absorption), a low volume node is a price with
little traded volume, and the FVG == LVN bridge is a claim about volume at price. The
certified XAUUSD data the harness serves (concept_lab.load_m1) carries open/high/low/close
only - no volume or tick-count column - and OTC spot gold has no consolidated volume at all.
A time-at-price (TPO) profile built from M1 would measure a different object (dwell time,
not absorbed size), so substituting it would test a concept the guest did not state.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

if __name__ == "__main__":
    m1 = cl.load_m1()
    assert "volume" not in m1.columns, "volume present - this concept should be tested"
    p = cl.write_untestable(
        "volume-profile-ledge",
        "needs volume-at-price data: the certified XAUUSD M1 is OHLC only (no volume/tick "
        "count; spot gold has no consolidated volume). Ledges and low-volume nodes are "
        "defined by traded volume at price; a TPO/time-at-price proxy would test a different object.",
        script=__file__,
        notes="load_m1() columns = open/high/low/close, checked in-script.")
    print(p)
