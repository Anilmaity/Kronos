import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sens import *
if __name__ == "__main__":
    m1 = cl.load_m1(); COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    base = build(m1)
    xt = pd.DatetimeIndex(base["ext_start"]); dirn = base["direction"].to_numpy()
    xh = cl.build_bars(m1, "1h"); hx = xh["high"].reindex(xt).to_numpy(); lx = xh["low"].reindex(xt).to_numpy()
    p = cl.prior_hilo(xt, "1D"); mk = np.where(dirn == -1, hx >= p["high"].to_numpy(), lx <= p["low"].to_numpy())
    summ("PDHL_tod30", cl.trade_test(base.loc[mk, COLS].reset_index(drop=True), max_hold="10h", ctrl_tod_tol_min=30))
    for rr in (1.5,): summ(f"rr{rr}_tod30", cl.trade_test(base[COLS].assign(rr=rr), max_hold="10h", ctrl_tod_tol_min=30))
    summ("hold20h_tod30", cl.trade_test(base[COLS], max_hold="20h", ctrl_tod_tol_min=30))
    summ("bars_tod30", cl.trade_test(base[COLS], max_hold="10h", hold_basis="bars", ctrl_tod_tol_min=30))
    summ("tod60", cl.trade_test(base[COLS], max_hold="10h", ctrl_tod_tol_min=60))
