"""Guarded scalping engine for XAUUSD — capped scale-in, NOT martingale.

WHY GUARDED: backtests (bt_scalp.py / bt_scalp_risk.py) show the z-score mean-reversion
scalp is NEGATIVE expectancy after costs even at 69-70% win rate (small TP + wide SL =
negative skew), and that an UNBOUNDED martingale 'averaging to recover' only looks
profitable until one sustained adverse run wipes the (leveraged) account. So this engine:

  * sizes every position by RISK (% of equity / stop distance), never by leverage headroom;
  * allows a LIMITED scale-in (averaging) at pre-defined offsets, with a HARD basket stop
    so the WHOLE basket's loss is capped at `max_basket_risk_pct` — no doubling to infinity;
  * enforces a daily-loss kill switch;
  * defaults to DRY-RUN. Live use should wait until an entry filter with a real edge exists.

100x leverage note: leverage only sets margin (0.01 lot XAU ~ $40 margin here), it does NOT
change risk — risk is stop_distance x size. We use leverage for capital efficiency only.

This is a tool/framework; it is intentionally conservative and is not auto-run by the goal loop.
"""
from dataclasses import dataclass, field


@dataclass
class ScalpConfig:
    risk_pct_per_basket: float = 1.0      # max % of equity lost if the basket stop hits
    tp_dollars: float = 3.0               # take-profit distance for the basket (avg price)
    stop_dollars: float = 9.0             # basket hard stop distance from FIRST entry
    max_adds: int = 2                     # extra scale-in legs (0 = single shot)
    add_offset_dollars: float = 4.0       # adverse move between scale-in legs
    add_fraction: float = 1.0             # each add = add_fraction x base lot (1.0 = flat avg, NOT doubling)
    daily_loss_kill_pct: float = 3.0      # stop trading for the day after this % loss
    entry_z: float = 2.0
    contract_size: float = 100.0          # 1 lot = 100 oz


@dataclass
class Basket:
    side: str
    legs: list = field(default_factory=list)  # list of (lot, price)
    open: bool = True

    def total_lot(self):
        return round(sum(L for L, _ in self.legs), 2)

    def avg_price(self):
        tl = self.total_lot()
        return sum(L * P for L, P in self.legs) / tl if tl else 0.0


class GuardedScalper:
    """Decision engine only — caller wires it to the broker (or dry-run). No I/O here."""

    def __init__(self, cfg: ScalpConfig, equity: float):
        self.cfg = cfg
        self.equity = equity
        self.day_pnl = 0.0
        self.basket: Basket | None = None

    def base_lot(self) -> float:
        """Size so that the FULL basket hitting its hard stop loses <= risk_pct_per_basket.
        Worst case the basket holds (1 + max_adds*add_fraction) base lots when stopped."""
        c = self.cfg
        worst_lots = 1 + c.max_adds * c.add_fraction
        risk_dollars = self.equity * c.risk_pct_per_basket / 100.0
        # loss if stopped ~ worst_lots*base * stop_dollars * contract/100  (per-0.01 = $1/$)
        lot = risk_dollars / (worst_lots * c.stop_dollars * c.contract_size / 100.0 * 100)
        # round to 0.01 step, floor, min 0.01
        return max(0.01, (int(lot * 100)) / 100.0)

    def killed_for_day(self) -> bool:
        return self.day_pnl <= -self.equity * self.cfg.daily_loss_kill_pct / 100.0

    def on_signal(self, z: float, price: float):
        """Return an action dict the caller executes, or None. Capped & guarded."""
        c = self.cfg
        if self.killed_for_day():
            return None
        if self.basket and self.basket.open:
            b = self.basket
            avg = b.avg_price()
            # basket take-profit
            tp_hit = (price >= avg + c.tp_dollars) if b.side == "long" else (price <= avg - c.tp_dollars)
            if tp_hit:
                return {"action": "close_basket", "reason": "tp"}
            # hard basket stop measured from FIRST leg (risk is pre-sized to this)
            first = b.legs[0][1]
            stop_hit = (price <= first - c.stop_dollars) if b.side == "long" else (price >= first + c.stop_dollars)
            if stop_hit:
                return {"action": "close_basket", "reason": "stop"}
            # limited scale-in at fixed offsets (NOT doubling): add when price moves
            # add_offset beyond the last leg, up to max_adds.
            if len(b.legs) - 1 < c.max_adds:
                last = b.legs[-1][1]
                adv = (price <= last - c.add_offset_dollars) if b.side == "long" else (price >= last + c.add_offset_dollars)
                if adv:
                    return {"action": "add_leg", "lot": round(self.base_lot() * c.add_fraction, 2), "price": price}
            return None
        # no basket -> open one on a z extreme
        if z <= -c.entry_z:
            return {"action": "open_basket", "side": "long", "lot": self.base_lot(), "price": price}
        if z >= c.entry_z:
            return {"action": "open_basket", "side": "short", "lot": self.base_lot(), "price": price}
        return None


if __name__ == "__main__":
    cfg = ScalpConfig()
    s = GuardedScalper(cfg, equity=5002.40)
    print("Guarded scalper self-check")
    print(f"  base lot for {cfg.risk_pct_per_basket}% basket risk, stop ${cfg.stop_dollars}, "
          f"max_adds {cfg.max_adds}: {s.base_lot()} lots")
    print(f"  worst-case basket loss if stopped ~ "
          f"${(1+cfg.max_adds*cfg.add_fraction)*s.base_lot()*cfg.stop_dollars*100:.2f} "
          f"(target <= ${s.equity*cfg.risk_pct_per_basket/100:.2f})")
    print("  NOTE: backtest verdict = z-MR scalp is -EV after costs; do NOT run live "
          "until an entry filter with a real edge is added. Leverage != more risk.")
