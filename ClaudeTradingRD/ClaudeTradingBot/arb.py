"""BTC edge-signal CLI — funding/positioning + 5-min model + cross-venue watch.

Read-only. Signals for paper validation, NOT trade instructions. See
bot/arbitrage.py for the methodology and the research caveats.

Usage: python arb.py
"""
import json
from bot import funding, arbitrage


def main():
    fund = funding.snapshot()
    sig = arbitrage.snapshot()

    print("=== PERP FUNDING / POSITIONING ===")
    pos = fund.get("positioning", {})
    if pos.get("score") is not None:
        print(f"  squeeze score {pos['score']:+.2f}  ->  {pos['label']}")
        fr = pos.get("funding", {})
        for v in ("binance", "bybit"):
            if isinstance(fr.get(v), dict):
                print(f"    {v}: funding {fr[v].get('rate')}")
    xs = (fund.get("cross_exchange") or {}).get("spread")
    if xs:
        print(f"  x-exchange spot spread: {xs['high_venue']} - {xs['low_venue']} "
              f"= ${xs['spread_usd']} ({xs['spread_bps']} bps)")

    print("\n=== 5-MIN BTC UP/DOWN — MODEL vs MARKET ===")
    ud = sig.get("updown_5m", {})
    print(f"  {ud.get('label', '')}")
    if ud.get("market_up_prob") is not None:
        print(f"  market UP {ud['market_up_prob']*100:.1f}%  "
              f"model UP {('%.1f%%' % (ud['model_up_prob']*100)) if ud.get('model_up_prob') is not None else 'n/a'}"
              f"  edge {('%.1f%%' % (ud['edge_up']*100)) if ud.get('edge_up') is not None else 'n/a'}"
              f"  -> {ud.get('flag', ud.get('status'))}")
    print(f"  sigma_$ {sig.get('sigma_dollar_per_sec')}/sec  spot {sig.get('spot')}")

    print("\n=== CROSS-VENUE PM DIVERGENCE (WATCH — basis risk) ===")
    cv = sig.get("cross_venue_pm", {})
    if cv.get("divergences"):
        for d in cv["divergences"]:
            print(f"  ${d['strike']:,}: Poly {d['poly_prob']*100:.0f}% vs "
                  f"Kalshi {d['kalshi_prob']*100:.0f}%  gap {d['gross_gap']*100:.0f}c "
                  f"(net {d['net_after_fees']*100:+.0f}c, basis_risk={d['basis_risk']})")
    else:
        print(f"  none past threshold ({cv.get('matched_strikes', 0)} matched strikes)")

    print(f"\n  {sig.get('disclaimer', '')}")
    print("\nJSON:", json.dumps({"funding": fund, "signals": sig}))


if __name__ == "__main__":
    main()
