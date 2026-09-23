exec(open("v3.py").read().split("pl, g = placebo")[0])
res = []
for sd in range(100, 112):
    pl, g = placebo("15min", 12, sd)
    r = cl.trade_test(pl, max_hold="150min", n_boot=500)
    res.append((sd, len(pl), r["diff"], r["ci_lo"], r["ci_hi"], r["verdict"]))
    print(res[-1]); sys.stdout.flush()
d = np.array([x[2] for x in res])
print("placebo diffs mean %.4f sd %.4f min %.4f max %.4f; frac >= 0.0806: %.2f" % (d.mean(), d.std(ddof=1), d.min(), d.max(), (d >= 0.0806).mean()))
json.dump(res, open(os.path.join(HERE, "v4_placebo_seeds.json"), "w"), default=str)
