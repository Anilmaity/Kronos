"""FVG ICT strategy — detect Fair Value Gaps on XAUUSD and trade the retest.

FVG detection mirrors KronosStrategies/strategies/strategy/ict_engine.py:
  Bullish FVG : candle[i-2].high < candle[i].low, middle candle bullish
  Bearish FVG : candle[i-2].low  > candle[i].high, middle candle bearish

Entry model (classic ICT FVG retest):
  - Only trade FVGs aligned with market structure (swing HH/HL vs LH/LL).
  - Wait for price to retrace INTO the gap, enter at the zone edge.
  - SL beyond the far side of the zone, TP at 2R.
  - An FVG is dead once fully filled (mitigated) or after MAX_AGE bars.

Outputs chart_data.js for chart.html (lightweight-charts) and prints a summary.
"""

from dataclasses import dataclass
import json

import pandas as pd
import yfinance as yf

SYMBOL = "GC=F"          # COMEX gold front-month as XAUUSD proxy
INTERVAL = "15m"
PERIOD = "60d"
MIN_GAP = 0.5            # min gap size in $ for a valid FVG (15m gold)
MAX_AGE = 96             # bars an unmitigated FVG stays tradeable (1 day of 15m)
RR = 2.0                 # take-profit at 2R
SL_BUFFER = 0.5          # $ beyond the zone
STRUCT_LOOKBACK = 3      # swing lookback for market structure
STRUCT_WINDOW = 60       # bars fed into the structure check


@dataclass
class FVG:
    type: str            # 'bullish' | 'bearish'
    zone_low: float
    zone_high: float
    born: int            # bar index of candle[i] (3rd candle)
    mitigated: int | None = None
    traded: bool = False


@dataclass
class Trade:
    side: str
    entry_idx: int
    entry: float
    sl: float
    tp: float
    exit_idx: int | None = None
    exit_px: float | None = None
    outcome: str | None = None   # 'TP' | 'SL' | 'OPEN'


def fetch_candles() -> pd.DataFrame:
    df = yf.download(SYMBOL, period=PERIOD, interval=INTERVAL,
                     progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
    df.index = df.index.tz_convert("UTC")
    return df.reset_index(names="time")


def swing_points(df: pd.DataFrame, lookback: int = STRUCT_LOOKBACK) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    out["swing_high"] = False
    out["swing_low"] = False
    for i in range(lookback, len(out) - lookback):
        window = out.iloc[i - lookback: i + lookback + 1]
        if out.at[i, "high"] == window["high"].max():
            out.at[i, "swing_high"] = True
        if out.at[i, "low"] == window["low"].min():
            out.at[i, "swing_low"] = True
    return out


def market_structure(df: pd.DataFrame) -> str:
    if len(df) < STRUCT_LOOKBACK * 2 + 3:
        return "ranging"
    sw = swing_points(df)
    highs = sw[sw["swing_high"]]["high"].values
    lows = sw[sw["swing_low"]]["low"].values
    if len(highs) < 2 or len(lows) < 2:
        return "ranging"
    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"
    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"
    return "ranging"


def detect_new_fvg(df: pd.DataFrame, i: int) -> FVG | None:
    c0, c1, c2 = df.iloc[i - 2], df.iloc[i - 1], df.iloc[i]
    if c2["low"] - c0["high"] >= MIN_GAP and c1["close"] > c1["open"]:
        return FVG("bullish", float(c0["high"]), float(c2["low"]), i)
    if c0["low"] - c2["high"] >= MIN_GAP and c1["close"] < c1["open"]:
        return FVG("bearish", float(c2["high"]), float(c0["low"]), i)
    return None


def run(df: pd.DataFrame) -> tuple[list[FVG], list[Trade]]:
    fvgs: list[FVG] = []
    trades: list[Trade] = []
    open_trade: Trade | None = None

    for i in range(2, len(df)):
        bar = df.iloc[i]

        # manage open trade first (conservative: SL wins if both hit in one bar)
        if open_trade:
            if open_trade.side == "BUY":
                if bar["low"] <= open_trade.sl:
                    open_trade.exit_idx, open_trade.exit_px, open_trade.outcome = i, open_trade.sl, "SL"
                elif bar["high"] >= open_trade.tp:
                    open_trade.exit_idx, open_trade.exit_px, open_trade.outcome = i, open_trade.tp, "TP"
            else:
                if bar["high"] >= open_trade.sl:
                    open_trade.exit_idx, open_trade.exit_px, open_trade.outcome = i, open_trade.sl, "SL"
                elif bar["low"] <= open_trade.tp:
                    open_trade.exit_idx, open_trade.exit_px, open_trade.outcome = i, open_trade.tp, "TP"
            if open_trade.outcome:
                open_trade = None

        # expire / mitigate existing zones
        for z in fvgs:
            if z.mitigated is None:
                if z.type == "bullish" and bar["low"] <= z.zone_low:
                    z.mitigated = i
                elif z.type == "bearish" and bar["high"] >= z.zone_high:
                    z.mitigated = i

        # entries: price retraces into a live, untraded, structure-aligned zone
        if open_trade is None:
            structure = market_structure(df.iloc[max(0, i - STRUCT_WINDOW): i])
            for z in fvgs:
                if z.traded or z.mitigated is not None or i - z.born > MAX_AGE or i == z.born:
                    continue
                if z.type == "bullish" and structure == "bullish" and bar["low"] <= z.zone_high:
                    entry = min(z.zone_high, float(bar["open"]))
                    sl = z.zone_low - SL_BUFFER
                    open_trade = Trade("BUY", i, entry, sl, entry + RR * (entry - sl))
                elif z.type == "bearish" and structure == "bearish" and bar["high"] >= z.zone_low:
                    entry = max(z.zone_low, float(bar["open"]))
                    sl = z.zone_high + SL_BUFFER
                    open_trade = Trade("SELL", i, entry, sl, entry - RR * (sl - entry))
                if open_trade:
                    z.traded = True
                    trades.append(open_trade)
                    break

        # new FVG born on this bar
        z = detect_new_fvg(df, i)
        if z:
            fvgs.append(z)

    if open_trade and open_trade.outcome is None:
        open_trade.outcome = "OPEN"
        open_trade.exit_idx = len(df) - 1
        open_trade.exit_px = float(df.iloc[-1]["close"])
    return fvgs, trades


def export(df: pd.DataFrame, fvgs: list[FVG], trades: list[Trade]) -> None:
    ts = [int(t.timestamp()) for t in df["time"]]
    candles = [{"time": ts[i], "open": round(float(r["open"]), 2),
                "high": round(float(r["high"]), 2), "low": round(float(r["low"]), 2),
                "close": round(float(r["close"]), 2)}
               for i, r in df.iterrows()]
    zones = [{"type": z.type, "low": z.zone_low, "high": z.zone_high,
              "from": ts[z.born],
              "to": ts[z.mitigated if z.mitigated is not None
                       else min(z.born + MAX_AGE, len(df) - 1)],
              "traded": z.traded}
             for z in fvgs]
    markers = []
    for t in trades:
        markers.append({"time": ts[t.entry_idx], "position": "belowBar" if t.side == "BUY" else "aboveBar",
                        "shape": "arrowUp" if t.side == "BUY" else "arrowDown",
                        "color": "#2196F3", "text": f"{t.side} @{t.entry:.1f}"})
        if t.exit_idx is not None:
            color = {"TP": "#4CAF50", "SL": "#F44336", "OPEN": "#9E9E9E"}[t.outcome]
            markers.append({"time": ts[t.exit_idx], "position": "aboveBar" if t.side == "BUY" else "belowBar",
                            "shape": "circle", "color": color,
                            "text": f"{t.outcome} @{t.exit_px:.1f}"})
    payload = {"symbol": SYMBOL, "interval": INTERVAL,
               "candles": candles, "fvgs": zones, "markers": markers}
    with open("chart_data.js", "w") as f:
        f.write("const CHART_DATA = " + json.dumps(payload) + ";")


def summary(trades: list[Trade]) -> str:
    closed = [t for t in trades if t.outcome in ("TP", "SL")]
    wins = sum(1 for t in closed if t.outcome == "TP")
    r_total = sum(RR if t.outcome == "TP" else -1.0 for t in closed)
    wr = 100 * wins / len(closed) if closed else 0.0
    return (f"trades={len(trades)} closed={len(closed)} wins={wins} "
            f"WR={wr:.1f}% net={r_total:+.1f}R (RR={RR})")


if __name__ == "__main__":
    df = fetch_candles()
    print(f"{SYMBOL} {INTERVAL}: {len(df)} candles "
          f"{df['time'].iloc[0]} → {df['time'].iloc[-1]}")
    fvgs, trades = run(df)
    live = sum(1 for z in fvgs if z.mitigated is None)
    print(f"FVGs detected={len(fvgs)} (unmitigated={live})")
    print(summary(trades))
    export(df, fvgs, trades)
    print("wrote chart_data.js — open chart.html to view")
