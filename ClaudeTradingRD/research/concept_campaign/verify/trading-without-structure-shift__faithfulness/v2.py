exec(open("v1.py").read().split("ev0 = detect_with()")[0].replace('d["blocks"] = {h: round(v["diff"], 4)', 'd["blocks"] = {h: round(v.get("diff") or np.nan, 4)'))
ev0 = detect_with()
ny = cl.to_ny(pd.DatetimeIndex(ev0.decision_time))
h = pd.Series(ny.hour).value_counts(normalize=True).sort_index()
print("event NY-hour share:", (h*100).round(1).to_dict())
# M1 trading minutes share per NY hour (baseline)
mh = pd.Series(cl.to_ny(m1.index).hour).value_counts(normalize=True).sort_index()
print("lift by hour:", (h / mh).round(2).to_dict())
r = run("ORIG_exB2", ev0[~((ev0.decision_time >= "2018-08-22") & (ev0.decision_time < "2021-04-12")).to_numpy()].reset_index(drop=True))
# faithfulness variants
for nm, g in [("TF5m", dict(TF="5min")), ("ret3", dict(RET_BARS=3)), ("ret6", dict(RET_BARS=6)),
              ("fill6", dict(FILL_BARS=6)), ("fill24", dict(FILL_BARS=24))]:
    ev = detect_with(**g)
    hold = "50min" if nm == "TF5m" else "150min"
    rr_ = run(nm, ev, max_hold=hold)
    run(nm + "_tod30", ev, max_hold=hold, ctrl_tod_tol_min=30)
json.dump(OUT, open(os.path.join(HERE, "v2_out.json"), "w"), default=str, indent=1)
