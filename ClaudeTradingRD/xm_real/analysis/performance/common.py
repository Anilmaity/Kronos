"""Shared loaders for the XM Real performance study. All times UTC. Inputs are read-only."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent            # .../xm_real
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
OZ = 100.0                          # GOLD contract size: 1 lot = 100 oz (verified by profit/pts/volume)
LEV = 1000.0                        # account leverage (verified against broker stop-out comments)


def load_deals():
    d = pd.DataFrame(json.load(open(SRC / "deals_raw.json"))["deals"])
    d["time"] = pd.to_datetime(d["time"], utc=True, format="ISO8601")
    d["cash"] = d.profit.fillna(0) + d.swap.fillna(0) + d.commission.fillna(0)
    return d.sort_values(["time", "id"]).reset_index(drop=True)


def load_positions():
    t = pd.read_csv(SRC / "trades.csv")
    for c in ("open_time", "close_time"):
        t[c] = pd.to_datetime(t[c], utc=True, format="ISO8601")
    t["sgn"] = t.side.map({"BUY": 1, "SELL": -1})
    t["closeby"] = t.exit_entry_type.eq("DEAL_ENTRY_OUT_BY")
    t["exit_kind"] = np.where(t.closeby, "CLOSE_BY", t.exit_reason.str.replace("DEAL_REASON_", ""))
    return t.sort_values("open_time").reset_index(drop=True)


def load_s5():
    return pd.read_parquet(SRC / "xau_s5_2026-11-03_now_ba.parquet").set_index("time").sort_index()


def load_basis():
    return json.load(open(OUT / "basis.json"))


def xm_quotes(s5=None):
    """OANDA S5 bid/ask shifted onto XM's quote (basis measured by 01_basis.py)."""
    s5 = load_s5() if s5 is None else s5
    b = load_basis()
    q = pd.DataFrame(index=s5.index)
    for f in ("open", "high", "low", "close"):
        q["bid_" + f] = s5["bid_" + f] + b["bid"]
        q["ask_" + f] = s5["ask_" + f] + b["ask"]
    return q


def md(df, floatfmt=".2f", index=True):
    """Small markdown table writer (no tabulate dependency)."""
    df = df.reset_index() if index else df
    def f(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else format(v, floatfmt)
        return str(v)
    rows = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    rows += ["| " + " | ".join(f(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(rows)
