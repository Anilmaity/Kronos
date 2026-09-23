import sys, importlib.util
sys.path.insert(0,'/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b')
spec=importlib.util.spec_from_file_location("orig","/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/entry_own_03b/no-shorting-below-lows.py")
orig=importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
cl=orig.cl
ev=orig.detect(cl.load_m1())
ev.to_pickle('orig_ev.pkl')
print(len(ev), ev.chase_day.mean(), cl.frame_fingerprint(ev) if hasattr(cl,'frame_fingerprint') else '')
res=cl.gate_test(ev,"chase_day",mask_available_at="decision_time",max_hold="150min",claim="-")
for k in ["n","diff","ci_lo","ci_hi","p","verdict","events_fp","mask_fp"]: print(k,res.get(k))
print(res["halves"]["H1"]["diff"],res["halves"]["H2"]["diff"], res["ties"]["verdict_stop_first"])
