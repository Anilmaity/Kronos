import sys, json
d = json.load(sys.stdin)
def g(x): return float('nan') if x is None else x
def gv(dd, k): return g(dd.get(k))
t=d['train']; o=d['oos']; st=d['oos_stress']
tg=d['train_spread_grid']; og=d['oos_spread_grid']
def tk(gr,s):
    try: return g(gr[s]['taker']['pf'])
    except Exception: return float('nan')
print('| TR N%3d pf%.2f tk20/30 %.2f/%.2f | OOS N%3d pf%.2f tk20/30 %.2f/%.2f tpd%.2f mDD%.0f | stress net%.1f pf%.2f'%(
   gv(t,'trades'), gv(t,'pf'), tk(tg,'0.20'), tk(tg,'0.30'),
   gv(o,'trades'), gv(o,'pf'), tk(og,'0.20'), tk(og,'0.30'), gv(o,'trades_per_day'), gv(o,'maxDD$'),
   gv(st,'net$'), gv(st,'pf')))
