"""Plot the M3 FVG+OB wide-hours config in a native lightweight-charts window.

Data payload from the Kronos session's m3_combo_chart_export.py.
Zones: FVG bull/bear = green/red; OB bull/bear = teal/purple.
Markers: blue arrows = FVG entries, purple arrows = OB entries,
circles = exits (green win / red loss).

Usage:  .venv/Scripts/python plot_m3_combo.py [data.json] [--shot]
"""
import json
import os
import sys
import threading
import time
from pathlib import Path

import pandas as pd
from lightweight_charts import Chart

# comma-separated periods, e.g. M3_EMAS="9,21" (default 20,200)
EMAS = [int(x) for x in os.getenv("M3_EMAS", "20,200").split(",") if x.strip()]
EMA_COLORS = ["#f0b90b", "#e91e63", "#00bcd4", "#8bc34a"]
RSI_N = int(os.getenv("M3_RSI", "14"))     # 0 disables the RSI pane


def wilder_rsi(close: pd.Series, n: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    ag = gain.ewm(alpha=1.0 / n, adjust=False).mean()
    al = loss.ewm(alpha=1.0 / n, adjust=False).mean()
    rs = ag / al.replace(0.0, 1e-12)
    return (100.0 - 100.0 / (1.0 + rs)).round(2)

DEFAULT_DATA = (Path(r"C:\Users\ANILM\AppData\Local\Temp\claude"
                     r"\E--Projects-Kronos"
                     r"\b59ab53a-27a5-4d2c-b44c-cd379a733825\scratchpad"
                     r"\m3_combo_chart_data.json"))

STYLE = {
    ("fvg", 1): ("rgba(76,175,80,0.20)", "rgba(76,175,80,0.7)"),
    ("fvg", -1): ("rgba(244,67,54,0.20)", "rgba(244,67,54,0.7)"),
    ("ob", 1): ("rgba(0,188,212,0.22)", "rgba(0,188,212,0.8)"),
    ("ob", -1): ("rgba(186,104,200,0.22)", "rgba(186,104,200,0.8)"),
}


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--shot"]
    path = Path(args[0]) if args else DEFAULT_DATA
    d = json.loads(path.read_text(encoding="utf-8"))

    df = pd.DataFrame(d["candles"])
    df["date"] = (pd.to_datetime(df.pop("time"), unit="s")
                  .astype("datetime64[ns]"))          # [ns] or the lib mangles

    chart = Chart(width=1500, height=880, inner_width=1,
                  inner_height=0.78 if RSI_N else 1.0,
                  toolbox=True, title=d["title"])
    chart.layout(background_color="#131722", text_color="#d1d4dc")
    chart.candle_style(up_color="#26a69a", down_color="#ef5350",
                       border_up_color="#26a69a", border_down_color="#ef5350",
                       wick_up_color="#26a69a", wick_down_color="#ef5350")
    chart.grid(vert_enabled=False, horz_enabled=False)
    chart.legend(False)
    chart.topbar.textbox("info", d["title"])
    chart.set(df)

    # EMAs on M3 closes, drawn as overlay lines
    for period, color in zip(EMAS, EMA_COLORS):
        name = f"EMA {period}"
        line = chart.create_line(name=name, color=color, width=1,
                                 price_line=False, price_label=False)
        edf = pd.DataFrame({
            "date": df["date"],
            name: df["close"].ewm(span=period, adjust=False).mean().round(2),
        }).iloc[period:]           # drop the warmup head
        line.set(edf)

    # RSI pane — same timeframe as the main pane, so logical sync is exact
    if RSI_N:
        rp = chart.create_subchart(position="below", width=1, height=0.22,
                                   sync=True)
        rp.layout(background_color="#131722", text_color="#d1d4dc")
        rp.grid(vert_enabled=False, horz_enabled=False)
        rp.legend(False)
        rname = f"RSI {RSI_N}"
        rline = rp.create_line(name=rname, color="#ce93d8", width=1,
                               price_line=False, price_label=True)
        rdf = pd.DataFrame({"date": df["date"],
                            rname: wilder_rsi(df["close"], RSI_N)}).iloc[RSI_N:]
        rline.set(rdf)
        rp.horizontal_line(70, color="rgba(244,67,54,0.5)", width=1)
        rp.horizontal_line(30, color="rgba(76,175,80,0.5)", width=1)

    bar_times = set(df["date"])
    t0, t_last = df["date"].iloc[0], df["date"].iloc[-1]

    def snap(unix_s: int) -> pd.Timestamp:
        t = pd.to_datetime(unix_s, unit="s").floor("3min")
        while t not in bar_times and t0 < t:
            t -= pd.Timedelta(minutes=3)          # gaps: previous real bar
        return max(t, t0)

    for z in d["zones"]:
        fill, edge = STYLE[(z["model"], z["side"])]
        chart.box(start_time=snap(z["from"]), end_time=min(snap(z["to"]), t_last),
                  start_value=z["high"], end_value=z["low"],
                  color=edge, fill_color=fill, width=1)

    pos_map = {"belowBar": "below", "aboveBar": "above"}
    shape_map = {"arrowUp": "arrow_up", "arrowDown": "arrow_down",
                 "circle": "circle"}
    # Allocate each marker a real, unused bar slot (forward within the data),
    # then emit in ascending time — out-of-order or off-data marker times
    # throw inside the lib's JS bridge.
    bar_list = list(df["date"])
    bar_index = {t: i for i, t in enumerate(bar_list)}
    # High-frequency specs generate 1500+ markers; the JS bridge chokes past
    # ~1000 and the text becomes unreadable anyway. Render markers only for
    # the last M3_MARKER_DAYS days (zones always draw for the full window).
    mdays = float(os.getenv("M3_MARKER_DAYS", "5"))
    cutoff = (df["date"].iloc[-1] - pd.Timedelta(days=mdays)).timestamp()
    markers_in = [m for m in d["markers"] if m["time"] >= cutoff]
    used = set()
    placed = []
    for m in sorted(markers_in, key=lambda x: x["time"]):
        i = bar_index.get(snap(m["time"]), 0)
        while i in used and i < len(bar_list) - 1:
            i += 1
        while i in used:                      # data end: walk backward
            i -= 1
        used.add(i)
        placed.append((i, m))
    for i, m in sorted(placed, key=lambda x: x[0]):
        chart.marker(time=bar_list[i],
                     position=pos_map.get(m["position"], "below"),
                     shape=shape_map.get(m["shape"], "circle"),
                     color=m["color"], text=m["text"])

    # open on the final ~2.5 days at readable zoom
    chart.run_script(
        f"{chart.id}.chart.timeScale().setVisibleLogicalRange("
        f"{{from: {len(df) - 1200}, to: {len(df) + 10}}});")

    if "--shot" in sys.argv:
        def shot():
            time.sleep(7)
            try:
                out = Path(__file__).parent / "m3_combo_native.png"
                out.write_bytes(chart.screenshot())
                print(f"saved {out}")
            except Exception as e:
                print(f"screenshot failed: {e}")
        threading.Thread(target=shot, daemon=True).start()

    chart.show(block=True)


if __name__ == "__main__":
    main()
