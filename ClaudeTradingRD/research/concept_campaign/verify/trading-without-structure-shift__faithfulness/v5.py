exec(open("v3.py").read().split("pl, g = placebo")[0].replace(" if tfname == \"15min\" else None", ""))
tw.TF = "5min"


res = []
for sd in range(200, 208):
    pl, g = placebo("5min", 12, sd)
    r = cl.trade_test(pl, max_hold="50min", n_boot=500)
    res.append((sd, len(g), len(pl), r["diff"], r["ci_lo"], r["ci_hi"], r["verdict"]))
    print(res[-1]); sys.stdout.flush()
d = np.array([x[3] for x in res])
print("5m placebo diffs mean %.4f sd %.4f max %.4f; frac >= 0.0414: %.2f" % (d.mean(), d.std(ddof=1), d.max(), (d >= 0.0414).mean()))
json.dump(res, open(os.path.join(HERE, "v5_placebo5m.json"), "w"), default=str)
