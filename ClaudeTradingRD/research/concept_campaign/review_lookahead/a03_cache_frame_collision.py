"""cache_frame keys are free-form and carry no fingerprint of the build function.
Two agents (separate processes) using the same natural key for different
detectors: the second silently receives the first agent's events. Also: an agent
that FIXES a lookahead bug in its detector and reruns gets the old buggy frame."""
import os, subprocess, sys
PY = "/Users/anil/Projects/Kronos/ClaudeTradingRD/.venv/bin/python"
env = dict(os.environ, CONCEPT_LAB_CACHE=os.path.abspath("scratch_cache"))
for f in os.listdir("scratch_cache"):
    os.unlink(os.path.join("scratch_cache", f))
agent = r'''
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import pandas as pd, concept_lab as cl
tag = sys.argv[1]
out = cl.cache_frame("fvg_15m", lambda: pd.DataFrame({"who_built_me": [tag], "shift": [int(sys.argv[2])]}))
print(f"agent {tag} asked for its own detector (shift={sys.argv[2]}), got:", out.to_dict("records"))
'''
subprocess.run([PY, "-c", agent, "A_buggy_shift-1", "-1"], env=env, check=True)
subprocess.run([PY, "-c", agent, "B_other_concept", "0"], env=env, check=True)
subprocess.run([PY, "-c", agent, "A_fixed_after_review", "0"], env=env, check=True)
print("files:", os.listdir("scratch_cache"))
