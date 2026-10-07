"""Verifier (faithfulness lens) for wick-trust-test u1007a. Ledger disabled; writes nothing to results."""
import os, sys, importlib.util
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

SCRIPT = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/update_20261007/wick-trust-test.py"
spec = importlib.util.spec_from_file_location("wtt", SCRIPT)
wtt = importlib.util.module_from_spec(spec); spec.loader.exec_module(wtt)

def events(htf="1D", ltf="1h"):
    wtt.HTF, wtt.LTF = htf, ltf
    return cl.cache_frame(f"verify_u1007a_{htf}_{ltf}", lambda: wtt.detect_a(cl.load_m1()))

def s(res):
    return {k: (round(res[k], 4) if isinstance(res.get(k), float) else res.get(k))
            for k in ("verdict", "n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "ctrl_overlap")}

if __name__ == "__main__":
    ev = events()
    print(len(ev), ev.trusted.sum(), cl.frame_fingerprint(ev))
    res = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold="10h", keep_trades=True)
    print(s(res)); tr = res["_trades"]; print(tr.columns.tolist()); print(tr.head())
    tr.to_pickle(os.path.join(os.path.dirname(__file__), "base_trades.pkl"))
