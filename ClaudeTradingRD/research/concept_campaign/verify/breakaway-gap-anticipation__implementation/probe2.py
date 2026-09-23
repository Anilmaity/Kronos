import numpy as np, pandas as pd
A = pd.read_pickle("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/breakaway-gap-anticipation__implementation/A.pkl")
A["ld"] = np.log(A.dist.clip(lower=1e-6)); A["ls"] = np.log(A["size"].clip(lower=1e-7))
A["mon"] = pd.DatetimeIndex(A.t).tz_convert(None).to_period("M").astype(str)
print("fill vs dist decile, overlap vs non:")
A["dq"] = pd.qcut(A.ld, 10, labels=False)
print(A.groupby(["dq", "ov"]).fill.mean().unstack().round(4).assign(n_ov=A[A.ov].groupby("dq").size(), n_non=A[~A.ov].groupby("dq").size()))
# stratified: month x dir x dist-decile, ATT weighting and ATC weighting
g = A.groupby(["mon", "dir", "dq", "ov"]).fill.agg(["mean", "size"]).unstack("ov")
g = g.dropna()
att = ((g[("mean", True)] - g[("mean", False)]) * g[("size", True)]).sum() / g[("size", True)].sum()
atc = ((g[("mean", True)] - g[("mean", False)]) * g[("size", False)]).sum() / g[("size", False)].sum()
print("stratified month x dir x dist-decile: ATT", round(att, 4), "ATC", round(atc, 4), "cells", len(g))
# logistic regression with month FE
import statsmodels.formula.api as smf
A["filli"] = A.fill.astype(int); A["ovi"] = A.ov.astype(int)
m = smf.logit("filli ~ ovi + ld + I(ld**2) + ls + C(dir) + C(mon)", data=A).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(A.t.dt.floor("5D") if hasattr(A.t, 'dt') else A.mon)[0]})
print("logit ovi coef", m.params["ovi"], "se", m.bse["ovi"], "p", m.pvalues["ovi"])
m2 = smf.logit("filli ~ ovi + ld + I(ld**2) + C(dir) + C(mon)", data=A).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(A.mon)[0]})
print("logit (no size) ovi coef", m2.params["ovi"], "se", m2.bse["ovi"], "p", m2.pvalues["ovi"])
# average marginal effect
me = m.get_margeff(at="overall").summary_frame().loc["ovi"]; print("AME ovi", me.to_dict())
