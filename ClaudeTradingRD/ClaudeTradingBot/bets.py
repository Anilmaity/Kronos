"""Live prediction-market BTC odds (Polymarket + Kalshi), for trade confluence.

Usage: python bets.py
Read-only. Prints an implied 'BTC above $X' CDF from each venue, each venue's
implied fair-value pivot, and the Polymarket US-Iran peace-deal probability
(the gold-down / BTC-up weekend binary).
"""
import json
from bot import polymarket, kalshi


def _print_cdf(cdf):
    if not cdf or not cdf.get("levels"):
        print("   (no live levels)")
        return
    for l in cdf["levels"]:
        p = l["prob_above"]
        bar = "#" * round(p * 20)
        k = l["threshold"] / 1000
        klab = f"{k:.0f}k" if k == int(k) else f"{k:.1f}k"
        print(f"   ${klab:>6}  {p*100:5.1f}%  {bar}")
    if cdf.get("implied_pivot"):
        extra = f"  (settles {cdf['settles']})" if cdf.get("settles") else ""
        print(f"   -> implied fair value ~= ${cdf['implied_pivot']:,.0f}{extra}")


def main():
    poly = polymarket.snapshot()
    kal = kalshi.snapshot()

    print("=== POLYMARKET ===")
    iran = poly.get("iran_deal")
    if iran:
        print(f"Iran permanent peace deal (risk-on if YES -> gold down / BTC up):")
        print(f"  nearest live: by {iran['headline_label']} = {iran['prob_yes']*100:.0f}% YES")
        ts = ", ".join(f"{t['label']} {t['prob_yes']*100:.0f}%"
                       for t in iran.get("term_structure", []) if 0 < t["prob_yes"] < 1)
        if ts:
            print(f"  term structure: {ts}")
    print(poly.get("btc_cdf", {}).get("title", "BTC"))
    _print_cdf(poly.get("btc_cdf"))

    print("\n=== KALSHI ===")
    if kal.get("quotes_available"):
        _print_cdf(kal.get("btc_cdf"))
    else:
        print("  " + kal.get("note", "no live quotes"))

    # machine-readable tail for piping
    print("\nJSON:", json.dumps({"polymarket": poly, "kalshi": kal}))


if __name__ == "__main__":
    main()
