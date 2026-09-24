"""Plain XAUUSD candles in a native lightweight-charts window — the base canvas for
sketching a new strategy. No indicators, lines, markers or extra panes; a timeframe
switcher sits in the top bar.

Style is KronosStrategies shared/db_utils.py::format_chart (mirrored here because
db_utils imports psycopg2 and loads .env at import time).

Times are shown in New York local time (DST-aware). 4h bars sit on the forex grid
(01/05/09/13/17/21 NY) and 1D bars are NY trading days rolling at 18:00.

Usage:  .venv/bin/python plot_xau.py [--tf 15m] [--shot]
        --shot saves xau_chart.png ~6s after load
"""
import argparse
import json
import threading
import time
from pathlib import Path

import pandas as pd
from lightweight_charts import Chart

HERE = Path(__file__).parent
DATA = HERE / "m3_scalper" / "xau_m1_full.parquet"
NY = "America/New_York"

# switcher label -> (pandas rule, resample offset in NY time, lookback in calendar days)
TIMEFRAMES = {
    "1m":  ("1min", None, 4),
    "3m":  ("3min", None, 8),
    "5m":  ("5min", None, 14),
    "15m": ("15min", None, 30),
    "30m": ("30min", None, 60),
    "1h":  ("1h", None, 120),
    "4h":  ("4h", "1h", 365),
    "1D":  ("1D", None, 365 * 3),
}


SF = ("-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', "
      "Arial, sans-serif")

# macOS toolbar chrome (apple-hig-designer): a light toolbar over the #DBDBDB canvas,
# the timeframe switcher as a segmented control — sunken track, raised white
# selected segment, concentric radii (7px outer = 5px inner + 2px padding).
MAC_CSS = """
:root { --label: #000; --label-2: rgba(60,60,67,.6); --sep: rgba(60,60,67,.18);
        --blue: #007AFF; --ease: cubic-bezier(.25,.1,.25,1); }
body { font-family: %(sf)s; -webkit-font-smoothing: antialiased; }
.topbar { background: #ECECEC; border-bottom: 1px solid var(--sep);
          min-height: 38px; padding: 0 8px; }
.topbar-seperator { display: none; }
.topbar-textbox { margin: 0 14px 0 6px; font-size: 13px; font-weight: 600;
                  letter-spacing: -.08px; color: var(--label); }
.mac-seg { display: inline-flex; gap: 0; padding: 2px; margin: 0 !important;
           background: rgba(0,0,0,.07); border-radius: 7px;
           box-shadow: inset 0 0 0 .5px rgba(0,0,0,.06); }
.mac-seg .switcher-button { margin: 0 !important; height: 22px; min-width: 34px !important;
           padding: 0 10px; border-radius: 5px; font: 500 12px/22px %(sf)s;
           color: var(--label); background: transparent;
           transition: background-color 120ms var(--ease), box-shadow 120ms var(--ease); }
.mac-seg .switcher-button:hover { background: rgba(0,0,0,.05); }
.mac-seg .switcher-button:active { background: rgba(0,0,0,.09); color: var(--label);
           font-weight: 500; }
.mac-seg .active-switcher-button { background: #FFFFFF !important; color: var(--label) !important;
           font-weight: 600; box-shadow: 0 .5px 1px rgba(0,0,0,.18), 0 1px 3px rgba(0,0,0,.08); }
.mac-seg .switcher-button:focus-visible { outline: 3px solid rgba(0,122,255,.45);
           outline-offset: 1px; }
.toolbox { background: rgba(255,255,255,.72); border: 1px solid var(--sep);
           border-left: none; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.toolbox-button:hover { background: rgba(0,0,0,.06); }
.toolbox-button g, .toolbox-button path { fill: rgba(60,60,67,.85); }
.active-toolbox-button { background: var(--blue) !important; }
.active-toolbox-button g, .active-toolbox-button path { fill: #fff; }
@media (prefers-reduced-motion: reduce) { * { transition-duration: .01ms !important; } }
""" % {"sf": SF}


def apply_mac_chrome(chart):
    css = json.dumps(MAC_CSS)
    # leading ';' — the lib concatenates queued scripts, so a bare '(' would be
    # parsed as a call on the previous statement (makeSwitcher(...)(...))
    chart.run_script(f"""
        ;(() => {{
          const s = document.createElement('style'); s.textContent = {css};
          document.head.appendChild(s);
          const b = document.querySelector('.switcher-button');
          if (b) {{
            const seg = b.parentElement;
            seg.classList.add('mac-seg');
            seg.setAttribute('role', 'radiogroup');
            seg.setAttribute('aria-label', 'Candle interval');
            seg.querySelectorAll('.switcher-button').forEach(x => {{
              x.setAttribute('role', 'radio');
              const on = x.classList.contains('active-switcher-button');
              x.setAttribute('aria-checked', on);
              x.addEventListener('click', () => seg.querySelectorAll('.switcher-button')
                .forEach(y => y.setAttribute('aria-checked', y === x)));
            }});
          }}
        }})();
    """)


def format_chart(chart):
    chart.layout(background_color="#DBDBDB", text_color="#000000",
                 font_size=11, font_family=SF)
    chart.candle_style(up_color="#089981", down_color="#000000",
                       border_up_color="#000000", border_down_color="#000000",
                       wick_up_color="#000000", wick_down_color="#000000")
    chart.grid(vert_enabled=False, horz_enabled=False)
    chart.legend(False)


def load_m1() -> pd.DataFrame:
    m1 = pd.read_parquet(DATA).set_index("time").sort_index()
    longest = max(days for _, _, days in TIMEFRAMES.values())
    m1 = m1[m1.index >= m1.index.max() - pd.Timedelta(days=longest)]
    m1.index = m1.index.tz_convert(NY)
    return m1


def candles(m1: pd.DataFrame, label: str) -> pd.DataFrame:
    rule, offset, days = TIMEFRAMES[label]
    src = m1[m1.index >= m1.index.max() - pd.Timedelta(days=days)]
    agg = dict(open=("open", "first"), high=("high", "max"),
               low=("low", "min"), close=("close", "last"))
    if rule == "1D":
        # NY trading day: 18:00 NY opens the next date's session (resample's
        # offset is ignored for non-tick freqs in pandas 3, so group explicitly)
        day = (src.index + pd.Timedelta(hours=6)).normalize().rename("time")
        bars = src.groupby(day).agg(**agg)
    else:
        bars = src.resample(rule, label="left", closed="left", offset=offset).agg(**agg)
    bars = bars.dropna()
    df = bars.reset_index().rename(columns={"time": "date"})
    # NY wall clock, tz-naive datetime64[ns] — [s] precision collapses the lib's time axis
    df["date"] = df["date"].dt.tz_localize(None).astype("datetime64[ns]")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="15m", choices=list(TIMEFRAMES))
    ap.add_argument("--shot", action="store_true")
    a = ap.parse_args()

    m1 = load_m1()
    chart = Chart(width=1500, height=900, toolbox=True, title="XAUUSD")
    format_chart(chart)

    def on_tf(c):
        c.set(candles(m1, c.topbar["tf"].value))

    chart.topbar.textbox("symbol", "XAUUSD")
    chart.topbar.switcher("tf", tuple(TIMEFRAMES), default=a.tf, func=on_tf)
    apply_mac_chrome(chart)
    chart.set(candles(m1, a.tf))

    if a.shot:
        def shot():
            time.sleep(6)
            try:
                (HERE / "xau_chart.png").write_bytes(chart.screenshot())
                print("saved xau_chart.png", flush=True)
            except Exception as e:
                print(f"screenshot failed: {e}", flush=True)
        threading.Thread(target=shot, daemon=True).start()

    chart.show(block=True)


if __name__ == "__main__":
    main()
