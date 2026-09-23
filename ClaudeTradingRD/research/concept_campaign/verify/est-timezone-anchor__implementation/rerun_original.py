import sys, runpy
sys.path.insert(0, '/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python')
import concept_lab as cl
cl.write_result = lambda *a, **k: "(write suppressed)"
runpy.run_path('/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_own_01a/est-timezone-anchor.py', run_name='__main__')
