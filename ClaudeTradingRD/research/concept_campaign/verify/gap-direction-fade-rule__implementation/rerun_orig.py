import sys, importlib.util
spec = importlib.util.spec_from_file_location("g", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_guest_02a/gap-direction-fade-rule.py")
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
f, res = g.run("a")
for k in ("n","observed_rate","null_rate","diff","ci_lo","ci_hi","p","mde","verdict","verdict_detail","ci_method"):
    print(k, res.get(k))
