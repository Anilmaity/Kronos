exec(open("indep2_tie.py").read().split("for kw in")[0])
for kw in [dict(),dict(buf_bp=1)]:
    AMB.clear(); t0,R,cR,risk=run(**kw)
    a=np.concatenate(AMB); n=len(R)
    print(kw,"TIE",TIE,boot(t0,R-cR.mean(1)),"amb real %.4f ctrl %.4f"%(a[:n].mean(),a[n:].mean()))
