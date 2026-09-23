"""Shared loader for the point-of-interest deep dive (read-only use of the campaign test)."""
import os, sys, importlib.util
DD = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = DD + "/dd_ledger.jsonl"      # never the campaign ledger
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b")
import numpy as np, pandas as pd
import concept_lab as cl

SCRIPT = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_01b/point-of-interest.py"
ANNOT = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/point-of-interest__faithfulness/annot.pkl"


def load_events():
    spec = importlib.util.spec_from_file_location("poi_mod", SCRIPT)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    p = DD + "/ev.pkl"
    if os.path.exists(p):
        ev = pd.read_pickle(p)
    else:
        ev = mod.detect(cl.load_m1()); ev.to_pickle(p)
    assert cl.frame_fingerprint(ev) == "5a57fd1f65a333b9", "event frame differs from the campaign result"
    an = pd.read_pickle(ANNOT)
    assert (an.poi_a.values == ev.poi_a.values).all()
    return ev, an


def day_boot_ci(x, days, n_boot=2000, seed=1):
    """Mean + 95% CI by bootstrapping whole trading days."""
    x = np.asarray(x, float); ok = np.isfinite(x); x = x[ok]; days = np.asarray(days)[ok]
    u, inv = np.unique(days, return_inverse=True)
    s = np.bincount(inv, weights=x); c = np.bincount(inv)
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        k = rng.integers(0, len(u), len(u))
        bs.append(s[k].sum() / c[k].sum())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return x.mean(), lo, hi, len(x)


def diff_boot_ci(xa, da, xb, db, n_boot=2000, seed=2):
    """mean(a)-mean(b), day-block bootstrap on each arm independently."""
    def prep(x, d):
        x = np.asarray(x, float); ok = np.isfinite(x)
        u, inv = np.unique(np.asarray(d)[ok], return_inverse=True)
        return np.bincount(inv, weights=x[ok]), np.bincount(inv)
    sa, ca = prep(xa, da); sb, cb = prep(xb, db)
    rng = np.random.default_rng(seed); bs = []
    for _ in range(n_boot):
        ka = rng.integers(0, len(sa), len(sa)); kb = rng.integers(0, len(sb), len(sb))
        bs.append(sa[ka].sum() / ca[ka].sum() - sb[kb].sum() / cb[kb].sum())
    d = sa.sum() / ca.sum() - sb.sum() / cb.sum()
    lo, hi = np.percentile(bs, [2.5, 97.5])
    se = np.std(bs)
    from math import erf, sqrt
    p = 2 * (1 - 0.5 * (1 + erf(abs(d) / se / sqrt(2))))
    return d, lo, hi, p
