exec(open("verify.py").read().split("base = ev")[0])
base = ev["open_exp"].to_numpy()
mod = cl.ny_minute_of_day(pd.DatetimeIndex(ev["decision_time"]))//60
print(pd.crosstab(mod, base, normalize="columns").round(3).T.to_string())
for lb, oc, stat in ((20,1.0,"mean"),(20,1.0,"q25"),(10,1.0,"median"),(30,1.0,"mean")):
    rf = asof_ref(ref_variant(lb, oc, stat), ev["decision_time"]); band = rf["band"].to_numpy(float)
    g = ev["day_covered"].to_numpy() < np.where(np.isfinite(band), band, np.inf)
    run(f"TOD30 lb{lb} opp{oc} {stat}", g, ctrl_tod_tol_min=30)
