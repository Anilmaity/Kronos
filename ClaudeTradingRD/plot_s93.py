"""Plot S93 FVG Scalp live-window mechanics in a native lightweight-charts window.

Data comes from a pre-exported JSON payload (built by the Kronos session's
s93_chart_export.py — M5 candles Jul 4-23 2026, killzone FVG boxes, the 20
live trades, and the validated SOFT M15-structure veto per box), so this
script only needs pandas + lightweight-charts (this repo's .venv).

Box colors:
  green / red shaded  — bullish / bearish FVG (killzone-qualifying)
  bold outline        — traded live
  grey shaded         — would be VETOED by the SOFT M15-structure rule
Markers: blue arrows = live entries, circles = exits (TP green / SL red /
TIME grey).

Usage:  .venv/Scripts/python plot_s93.py [data.json] [--shot]
        --shot saves s93_native.png ~6s after load (render verification)
"""

import json
import sys
import threading
import time
from pathlib import Path

import pandas as pd
from lightweight_charts import Chart

DEFAULT_DATA = (Path(r"C:\Users\ANILM\AppData\Local\Temp\claude"
                     r"\E--Projects-Kronos"
                     r"\b59ab53a-27a5-4d2c-b44c-cd379a733825\scratchpad"
                     r"\s93_chart_data.json"))


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--shot"]
    path = Path(args[0]) if args else DEFAULT_DATA
    d = json.loads(path.read_text(encoding="utf-8"))

    df = pd.DataFrame(d["candles"])
    # tz-naive datetime64[ns] — pandas 3 yields datetime64[s] from unit='s',
    # which the lib mangles into a single epoch bucket (same bug as RD's
    # yfinance note); force [ns] explicitly
    df["date"] = pd.to_datetime(df.pop("time"), unit="s").astype("datetime64[ns]")

    chart = Chart(width=1400, height=880, inner_width=1, inner_height=0.68,
                  toolbox=True, title=d["title"])
    chart.layout(background_color="#131722", text_color="#d1d4dc")
    chart.candle_style(up_color="#26a69a", down_color="#ef5350",
                       border_up_color="#26a69a", border_down_color="#ef5350",
                       wick_up_color="#26a69a", wick_down_color="#ef5350")
    chart.grid(vert_enabled=False, horz_enabled=False)
    chart.legend(False)
    chart.topbar.textbox(
        "info",
        f"S93 FVG Scalp · M5 · {len(d['fvgs'])} killzone FVGs · "
        f"{d['n_traded']} traded · {d['n_vetoed']} would be structure-vetoed "
        f"(grey) · TP green / SL red / TIME grey")
    chart.set(df)

    import os
    t0 = pd.Timestamp(df["date"].iloc[0])
    for z in ([] if os.getenv("S93_NO_BOXES") else d["fvgs"]):
        start = max(pd.to_datetime(z["from"], unit="s").floor("5min"), t0)
        end = pd.to_datetime(z["to"], unit="s").floor("5min")
        if end <= start:
            end = start + pd.Timedelta(minutes=5)
        if z["vetoed"]:
            fill = "rgba(158,158,158,0.25)"
            edge = "rgba(158,158,158,0.9)" if z["traded"] else fill
        elif z["type"] == "bullish":
            fill = "rgba(76,175,80,0.18)"
            edge = "rgba(76,175,80,0.9)" if z["traded"] else fill
        else:
            fill = "rgba(244,67,54,0.18)"
            edge = "rgba(244,67,54,0.9)" if z["traded"] else fill
        chart.box(start_time=start, end_time=end,
                  start_value=z["high"], end_value=z["low"],
                  color=edge, fill_color=fill, width=1)

    pos_map = {"belowBar": "below", "aboveBar": "above"}
    shape_map = {"arrowUp": "arrow_up", "arrowDown": "arrow_down",
                 "circle": "circle"}
    # marker/box times MUST land exactly on an existing M5 bar time —
    # off-bar times (signal stamps carry seconds) break the whole overlay.
    bar_times = set(df["date"])

    def snap(unix_s: int) -> pd.Timestamp:
        t = pd.to_datetime(unix_s, unit="s").floor("5min")
        while t not in bar_times and t > df["date"].iloc[0]:
            t -= pd.Timedelta(minutes=5)   # weekend/holiday gap: previous bar
        return t

    seen = set()
    for m in ([] if os.getenv("S93_NO_MARKERS")
              else sorted(d["markers"], key=lambda x: x["time"])):
        t = snap(m["time"])
        while t in seen:                   # markers on one bar: nudge forward
            t += pd.Timedelta(minutes=5)
        seen.add(t)
        chart.marker(time=t,
                     position=pos_map.get(m["position"], "below"),
                     shape=shape_map.get(m["shape"], "circle"),
                     color=m["color"], text=m["text"])

    # M15 zigzag — the exact swing skeleton the SOFT structure veto reads
    if d.get("zigzag") and not os.getenv("S93_NO_ZIGZAG"):
        zdf = pd.DataFrame(d["zigzag"])
        zdf["date"] = (pd.to_datetime(zdf.pop("time"), unit="s")
                       .astype("datetime64[ns]"))
        zz_line = chart.create_line(name="M15 zigzag", color="#f0b90b",
                                    width=2, price_line=False,
                                    price_label=False)
        zz_line.set(zdf[["date", "value"]].rename(columns={"value": "M15 zigzag"}))

    # H1 pane below (time-synced): candles + its own zigzag
    h1 = None
    if d.get("h1_candles") and not os.getenv("S93_NO_H1"):
        # sync=False on purpose: the lib syncs LOGICAL (bar-index) ranges,
        # which cannot line up across different timeframes — a synced H1
        # pane gets pushed past its own data by M5 indices.
        h1 = chart.create_subchart(position="below", width=1, height=0.32,
                                   sync=False)
        h1.layout(background_color="#131722", text_color="#d1d4dc")
        h1.candle_style(up_color="#26a69a", down_color="#ef5350",
                        border_up_color="#26a69a", border_down_color="#ef5350",
                        wick_up_color="#26a69a", wick_down_color="#ef5350")
        h1.grid(vert_enabled=False, horz_enabled=False)
        h1.legend(False)
        h1df = pd.DataFrame(d["h1_candles"])
        h1df["date"] = (pd.to_datetime(h1df.pop("time"), unit="s")
                        .astype("datetime64[ns]"))
        h1.set(h1df)
        if d.get("h1_zigzag"):
            hz = pd.DataFrame(d["h1_zigzag"])
            hz["date"] = (pd.to_datetime(hz.pop("time"), unit="s")
                          .astype("datetime64[ns]"))
            h1_line = h1.create_line(name="H1 zigzag", color="#f0b90b",
                                     width=2, price_line=False,
                                     price_label=False)
            h1_line.set(hz[["date", "value"]].rename(columns={"value": "H1 zigzag"}))

        # Continuous daily AMD zones (CRT frame):
        #   A blue = Asian range box, M orange = sweep + close-back excursion,
        #   D green = post-close-back expansion (bright when the opposite
        #   Asian extreme was hit — the CRT target; dim when it wasn't)
        if d.get("h1_amd") and not os.getenv("S93_NO_AMD"):
            AMD_STYLE = {
                "A": ("rgba(33,150,243,0.35)", "rgba(33,150,243,0.14)"),
                "M": ("rgba(255,152,0,0.85)", "rgba(255,152,0,0.28)"),
            }
            for z in d["h1_amd"]:
                if z["phase"] == "D":
                    edge, fill = (("rgba(76,175,80,0.85)", "rgba(76,175,80,0.22)")
                                  if z["hit"] else
                                  ("rgba(76,175,80,0.30)", "rgba(76,175,80,0.10)"))
                else:
                    edge, fill = AMD_STYLE[z["phase"]]
                h1.box(start_time=pd.to_datetime(z["from"], unit="s"),
                       end_time=pd.to_datetime(z["to"], unit="s"),
                       start_value=z["high"], end_value=z["low"],
                       color=edge, fill_color=fill, width=1)

    # initial view: full range on both panes (zoom in from there)
    if not os.getenv("S93_NO_RANGE"):
        chart.run_script(
            f"{chart.id}.chart.timeScale().setVisibleLogicalRange("
            f"{{from: 0, to: {len(df) + 10}}});")
        if h1 is not None:
            # open on the last ~3.5 weeks so the daily AMD zones are visible
            # (full 6 months stays loaded — pan left for the rest)
            n_h1 = len(d["h1_candles"])
            h1.run_script(
                f"{h1.id}.chart.timeScale().setVisibleLogicalRange("
                f"{{from: {max(0, n_h1 - 400)}, to: {n_h1 + 3}}});")

    if "--shot" in sys.argv:
        def shot():
            time.sleep(6)
            here = Path(__file__).parent
            try:
                (here / "s93_native.png").write_bytes(chart.screenshot())
                print("saved s93_native.png")
                if h1 is not None:
                    (here / "s93_native_h1.png").write_bytes(h1.screenshot())
                    print("saved s93_native_h1.png")
            except Exception as e:
                print(f"screenshot failed: {e}")
        threading.Thread(target=shot, daemon=True).start()

    chart.show(block=True)


if __name__ == "__main__":
    main()
