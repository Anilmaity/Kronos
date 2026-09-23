"""shallow-retracement — gate_test.

Concept (specified): during genuine expansion retracements are shallow; a pullback that
reaches the OTE of the impulse leg is not a retracement but a V-shape reversal and flips the
read. "Continuation entry only on a shallow retracement", stop behind the pullback extreme.

Baseline book (stated): 1h impulse legs — a confirmed 2/2 swing high CLOSED above (the
grade-A structural displacement gate), leg low L = lowest low from that swing to the break,
leg high H = the first confirmed swing high at/after the break with L intact. After the leg is
known (H's confirmation close), the first 5m CISD (phase-3 rung-0 config) in the leg's
direction whose protected swing (the pullback extreme) lies strictly inside (L, H), with price
not having exceeded H between H's bar and the pullback extreme, within 24 1h bars. Continuation
entry at the CISD close, stop = pullback extreme, 2R, 10 x 5m bars. Mirror for bearish legs.
Gate shallow: retracement depth (H - pullback) / (H - L) < 0.618 (the OTE boundary the concept
names). claim '+': shallow-pullback continuations beat deep (OTE-reaching) ones.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ns, empty, cisd_frame, bar_arrays, PHASE3_SRC  # noqa: E402

CID = "shallow-retracement"
HTF, LTF, HOLD, RR = "1h", "5min", "50min", 2.0
OTE = 0.618
WAIT_H = 24
RIGHT = 2
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "shallow", "depth"]


def legs(d: dict) -> list:
    """(dir, anchor, extreme, p_i, arm_i) structure-break impulse legs, arm = p + RIGHT."""
    h, l, c, sh, sl = d["h"], d["l"], d["c"], d["sh"], d["sl"]
    n = len(h)
    out = []
    for bull in (True, False):
        piv = sh if bull else sl
        cur, broken, seen = -1, True, set()
        for j in range(n):
            if cur >= 0 and not broken:
                lvl = h[cur] if bull else l[cur]
                if (c[j] > lvl) if bull else (c[j] < lvl):
                    broken = True
                    k = j
                    seg = l[cur:k + 1] if bull else h[cur:k + 1]
                    anchor = float(seg.min() if bull else seg.max())
                    p = k
                    while p + RIGHT < n and not piv[p]:
                        p += 1
                    if p + RIGHT < n and piv[p] and p not in seen:
                        arm = p + RIGHT
                        intact = (l[k:arm + 1].min() > anchor) if bull else (h[k:arm + 1].max() < anchor)
                        if intact:
                            seen.add(p)
                            out.append((1 if bull else -1, anchor, float(h[p] if bull else l[p]), p, arm))
            q = j - RIGHT
            if q >= 0 and piv[q]:
                cur, broken = q, False
    return out


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    hb = cl.build_bars(m1, HTF)
    lb = cl.build_bars(m1, LTF)
    if len(hb) < 20 or len(lb) < 50:
        return empty(COLS)
    d = bar_arrays(hb)
    ev = cisd_frame(lb)
    if ev.empty:
        return empty(COLS)
    lst, lh, ll = ns(lb.index), lb["high"].to_numpy(float), lb["low"].to_numpy(float)
    e_dir = ev["sgn"].to_numpy()
    e_ext = ev["ext_pos"].to_numpy()
    e_conf = ev["conf_pos"].to_numpy()
    e_ct = ns(ev["conf_close_time"])
    e_ps = ev["protected_swing"].to_numpy(float)
    rows = []
    for dr, L, H, p, arm in legs(d):
        t_arm = d["ct"][arm]
        t_end = d["ct"][min(arm + WAIT_H, len(d["ct"]) - 1)]
        cand = np.flatnonzero((e_dir == dr) & (e_ct >= t_arm) & (e_ct <= t_end) &
                              (lst[e_ext] >= d["st"][p]))
        for i in cand[np.argsort(e_ct[cand], kind="stable")]:
            ps = e_ps[i]
            if not ((L < ps < H) if dr == 1 else (H < ps < L)):
                continue
            a = int(np.searchsorted(lst, d["st"][p], "left"))
            seg = lh[a:e_ext[i] + 1] if dr == 1 else ll[a:e_ext[i] + 1]
            if (seg.max() > H) if dr == 1 else (seg.min() < H):
                continue                               # a new extreme: not a pullback from H
            depth = (H - ps) / (H - L)
            rows.append((e_ct[i], dr, ps, bool(depth < OTE), float(depth)))
            break
    if not rows:
        return empty(COLS)
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "shallow", "depth"])
    t = pd.DatetimeIndex(pd.to_datetime(out["t"].to_numpy(np.int64), utc=True))
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": out["direction"].to_numpy(),
                         "stop_px": out["stop_px"].to_numpy(), "rr": RR,
                         "shallow": out["shallow"].to_numpy(bool), "depth": out["depth"].to_numpy()}
                        ).sort_values("decision_time", kind="stable").reset_index(drop=True)[COLS]


OP = {"rules": [
    "1h bars, 2/2 fractal swings; impulse leg = close through the last confirmed swing high (bullish), "
    "anchor L = lowest low since that swing, extreme H = first confirmed swing high at/after the break with L intact",
    "after H's confirmation close, within 24 1h bars: first 5m CISD (series_open 2/2 max_wait 3) in the leg direction "
    "whose protected swing lies inside (L, H) and whose extreme formed after H with no new high above H before it",
    "decide at the CISD close, enter next M1 open, stop = pullback extreme, 2R, hold 10 x 5m",
    "gate shallow: (H - pullback) / (H - L) < 0.618; mirror for bearish"],
    "params": {"htf": HTF, "ltf": LTF, "ote": OTE, "wait_h": WAIT_H, "swing": "2/2", "rr": RR,
               "max_hold": HOLD, "cisd": "series_open 2/2 max_wait 3"}}
SRC = {"htf": "corpus: YAML htf [4H, 1H]; method_spec §1.2 pairing 1-hour -> 5-minute",
       "ltf": "method_spec: §1.2 pairing 1-hour -> 5-minute; YAML ltf includes 5m",
       "ote": "corpus: YAML 'a pullback reaching the OTE zone of the leg invalidates the expansion read'; threshold_fits §3 (OTE lower boundary 0.62)",
       "wait_h": "declared-before-run: the continuation entry must come within 24 1h bars of the leg being confirmed",
       "swing": PHASE3_SRC, "cisd": PHASE3_SRC, "rr": PHASE3_SRC, "max_hold": PHASE3_SRC,
       "impulse_leg": "threshold_fits: §2 structural displacement = close beyond the swing (grade A); §3 swing-to-swing legs"}

if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_1h_5m", lambda: detect(cl.load_m1()))
    print(len(ev), ev["shallow"].mean(), ev["depth"].describe().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"])
    res = cl.gate_test(ev, "shallow", mask_available_at="decision_time", max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap")})
    p = cl.write_result(CID, None, res, operationalization=OP, params_source=SRC, script=__file__, probe=probe,
                        notes=f"gate firing rate {ev['shallow'].mean():.3f}; median depth {ev['depth'].median():.3f}")
    print(p)
