"""Plot the FVG ICT strategy in a native lightweight-charts window.

Runs the strategy from fvg_ict.py, then renders:
  - candlesticks (XAUUSD proxy GC=F)
  - FVG zones as shaded boxes (green bullish / red bearish, outlined if traded)
  - trade entry/exit markers (TP green, SL red)

Usage:  python plot_fvg.py            # opens the interactive window
        python plot_fvg.py --shot     # also saves fvg_native.png after load
"""

import sys
import threading
import time

from lightweight_charts import Chart

from fvg_ict import MAX_AGE, RR, fetch_candles, run, summary


def main() -> None:
    df = fetch_candles()
    fvgs, trades = run(df)
    stats = summary(trades)
    print(f"candles={len(df)} fvgs={len(fvgs)} {stats}")

    # layout from KronosStrategies shared/db_utils.py::format_chart
    chart = Chart(width=1280, height=760, toolbox=True,
                  title="FVG ICT — XAUUSD (GC=F 15m)")
    chart.layout(background_color="#DBDBDB", text_color="#000000")
    chart.candle_style(up_color="#089981", down_color="#000000",
                       border_up_color="#000000", border_down_color="#000000",
                       wick_up_color="#000000", wick_down_color="#000000")
    chart.grid(vert_enabled=False, horz_enabled=False)
    chart.legend(False)
    chart.topbar.textbox("info", f"FVG ICT  ·  GC=F 15m  ·  {stats}")

    # lightweight-charts assumes tz-naive datetime64[ns]; pandas 3 + yfinance
    # deliver tz-aware datetime64[s], which the lib mangles into epoch~0
    df = df.copy()
    df["time"] = df["time"].dt.tz_localize(None).astype("datetime64[ns]")
    chart.set(df.rename(columns={"time": "date"}))

    # FVG zones — draw the most recent ones to keep the window responsive
    for z in fvgs[-150:]:
        end_idx = z.mitigated if z.mitigated is not None else min(z.born + MAX_AGE, len(df) - 1)
        fill = "rgba(76,175,80,0.18)" if z.type == "bullish" else "rgba(244,67,54,0.18)"
        edge = ("rgba(76,175,80,0.9)" if z.type == "bullish" else "rgba(244,67,54,0.9)") \
            if z.traded else fill
        chart.box(start_time=df["time"].iloc[z.born], end_time=df["time"].iloc[end_idx],
                  start_value=z.zone_high, end_value=z.zone_low,
                  color=edge, fill_color=fill, width=1)

    for t in trades:
        chart.marker(time=df["time"].iloc[t.entry_idx],
                     position="below" if t.side == "BUY" else "above",
                     shape="arrow_up" if t.side == "BUY" else "arrow_down",
                     color="#2196F3", text=f"{t.side} {t.entry:.1f}")
        if t.exit_idx is not None:
            color = {"TP": "#4CAF50", "SL": "#F44336", "OPEN": "#9E9E9E"}[t.outcome]
            chart.marker(time=df["time"].iloc[t.exit_idx],
                         position="above" if t.side == "BUY" else "below",
                         shape="circle", color=color,
                         text=f"{t.outcome} {t.exit_px:.1f}")

    # open focused on the recent action instead of all 60 days squeezed together
    chart.run_script(
        f"{chart.id}.chart.timeScale().setVisibleLogicalRange("
        f"{{from: {len(df) - 250}, to: {len(df) + 5}}});"
    )

    if "--shot" in sys.argv:
        def shot():
            time.sleep(6)
            try:
                with open("fvg_native.png", "wb") as f:
                    f.write(chart.screenshot())
                print("saved fvg_native.png")
            except Exception as e:
                print(f"screenshot failed: {e}")
        threading.Thread(target=shot, daemon=True).start()

    chart.show(block=True)


if __name__ == "__main__":
    main()
