"""Control-draw sensitivity of reading a (seed is locked for writing; this only measures dispersion)."""
src = open("robust.py").read()
head, _ = src.split('ev15 = build("15min")')
exec(head)
ev15 = build("15min")
for sd in [1, 2, 3, 4, 5, 6]:
    r = gt(ev15, "gate_a", seed=sd)
    print(sd, f"diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] p={r['p']:.3f} {r['verdict']}", flush=True)
