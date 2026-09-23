"""Build concept_verdicts.csv - the per-reading record of the 471-concept campaign (2026-09-23).

Reads only campaign outputs (never edits them):
  batches.json            category / voice per concept
  campaign_raw.json       tester rows (summary, script, result path) + verification votes
  campaign_adjusted.json  Holm / BH over the 864-hypothesis family (612 written + 252 ledger-only)
and adds the post-campaign layer by hand:
  EDGE_NOTES              one line per raw EDGE, written after 2-lens verification / deep dive
  DEEPDIVE                final label for the 5 BH-surviving, verifier-upheld EDGEs

    ../../.venv/bin/python concept_campaign/build_concept_verdicts.py   (from research/)
Writes concept_campaign/concept_verdicts.csv and prints the headline counts.
"""
import collections
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
load = lambda f: json.load(open(os.path.join(HERE, f)))

DEEPDIVE = {  # concept_id -> (label, one-line)
    "cheat-code-entry": ("ARTEFACT",
        "Deep dive: a structural control (stop at a fresh 15m extreme, same distance) removes 60-85% of +0.078R; "
        "residual +0.02-0.03R, negative in 2024; median stop 0.435pt so a 0.30pt spread nets -2.3R/trade. Not tradeable."),
    "aggressive-run-hammer-signature": ("ARTEFACT",
        "Deep dive: vs a generic faded 3-bar mini-sweep with a wick stop the diff is +0.010 [-0.001,+0.020], H2 -0.007; "
        "edge lives in sub-1pt stops, gross ~0 at risk>=2pt, net -0.08 to -0.11R. Not tradeable."),
    "point-of-interest": ("DESCRIPTIVE_ONLY",
        "Deep dive: the gate split survives structural controls (+0.10 to +0.12R) but is a negative filter - CISDs off a "
        "non-extreme HL/LH lose ~0.08R; gated book gross +0.042R nets -0.009R at 0.30pt. BH q=0.049, Holm fails."),
    "daily-profile-session-windows": ("DESCRIPTIVE_ONLY",
        "Deep dive: +12.1pp is real but a volatility-only null explains 83% of it; residual +1.8pp decays to +0.2pp in B4. "
        "No entry beats a structural control; net -0.08 to -0.38R at 0.30pt."),
    "fvg-three-levels": ("DESCRIPTIVE_ONLY",
        "Deep dive: leg extreme is reached before a far-edge close 1-2pp more often, surviving structural controls "
        "(+1.05 to +1.80pp); no trade beats a structural-stop control, median stop 0.655pt so every book is net negative."),
}

EDGE_NOTES = {  # (concept_id, reading) -> post-verification one-liner
    ("gb-range-return-entry", ""): "Refuted (both lenses): the effect sits in stale limit fills after the range was already invalidated / target traded; the faithful subset is +0.000R.",
    ("mitigation-block", "a"): "Refuted (both): the aggressive-trend gate adds nothing - the same fill mechanics on every opposing candle give a larger EDGE (+0.030R); stop-through fills are dropped.",
    ("trend-entry-options", ""): "Refuted (both): reduces to the cheat-code first opposing candle; the whole effect is in the smallest-stop quintile (median stop 0.11pt).",
    ("no-shorting-below-lows", "b"): "Verifiers upheld (-0.038R, all 4 blocks negative) but BH q=0.16 - a candidate only: shorting 15m CISDs at the running day low underperforms.",
    ("breakaway-gap-anticipation", ""): "Refuted (both): nearest-neighbour null has a far-tail boundary bias; placebo blocks give the same effect and a 20-bar lookback kills it.",
    ("mechanical-trade-management", "a"): "Refuted (both): the test compared new entries with random entries, not fixed-R vs break-even on the same entries; the paired comparison is +0.026 [-0.011,+0.062].",
    ("harder-target-behind-protected-swing", ""): "Refuted (both): the -1pp belongs to old untaken levels; unguarded untaken swings fall short of the null by more (-1.96pp).",
    ("fair-value-gap", "b"): "Refuted (both): volatility clustering after displacement - a local-volatility-matched null gives -0.005 NULL.",
    ("order-block", "b"): "Refuted (implementation lens): disappears under the time-of-day-matched control (trap 9).",
    ("opposing-run", ""): "Refuted (faithfulness): a knife-edge 0.30 cut - every neighbouring cut and the futures 4H grid are NULL.",
    ("inversion-fair-value-gap", "b"): "Verifiers upheld but weak (+0.018R, CI low +0.001, H2 not significant, NULL with hold_basis=bars); BH q=0.20.",
    ("volume-imbalance", ""): "Refuted (both): feed noise at 15m candle boundaries in 2016-18 (stops 2-4x the open/close gap); effect exists only in B1.",
    ("balanced-price-range-overlap", "a"): "Verifiers upheld (+0.024R, independent build identical) but H2 +0.0006 and BH q=0.11 - candidate only.",
    ("old-high-low-three-outcomes", ""): "Refuted (both): rests on the locked-seed control draw; ToD-matched control halves it to NULL.",
    ("po3-four-hour-opening-times", "a"): "Refuted (faithfulness): every entry is 10:00 NY and the ToD-matched control removes it; tests a superset of the concept.",
    ("breaker-block", "a"): "Refuted (faithfulness): a placebo without the breaker's higher high gives the same edge; 2021 alone carries 37%.",
    ("poi-density-by-timeframe", ""): "Refuted (faithfulness): the CISD-level POI branch passes almost automatically (29% of events pass with no POI).",
    ("dont-trade-after-expansion", "b"): "Refuted (faithfulness): the concept's own condition (late in the expanded candle) carries none of the effect.",
    ("internal-range-liquidity", "a"): "Refuted (both): NULL once the null is time-of-day matched or drawn from other purge bars.",
    ("internal-range-liquidity", "b"): "Refuted (both): NULL once the null is time-of-day matched (+0.7pp [-0.6,+2.1]).",
    ("fractal-model-c2", "a"): "Refuted (both): forex 4H grid only - futures and UTC grids NULL; fails the ToD-matched control.",
    ("sons-model", ""): "Refuted (both): with a ToD-matched control H2 turns negative; all of it is 2016-2021; the bare trigger earns ~40%.",
    ("target-liquidity-and-imbalances", "b"): "Refuted (faithfulness): non-FVG bars with matched geometry show almost the same lift - it is 'revisit the last bar's extreme'.",
    ("advanced-market-structure-labeling", "a"): "Refuted (faithfulness): any 3-bar swing does better (+0.023R); the faithful reading b is NULL.",
    ("failure-swing", "b"): "Refuted (faithfulness): only one horizon is EDGE; 1H and neighbouring horizons NULL; B1 negative.",
    ("propulsion-block", "a"): "Refuted (both): a placebo with the same limit-fill mechanics and no block gives +0.025; ToD control NULL.",
    ("propulsion-block", "b"): "Refuted (both): the limit-fill emulation (dropping fills that close through the stop) produces the edge, not the block.",
    ("daily-profile-session-windows", ""): None,
    ("est-timezone-anchor", "a"): "Refuted (faithfulness): measures the 08:30 volatility step of a sibling concept, not the clock convention; the null ignores time of day.",
    ("est-timezone-anchor", "b"): "Refuted (faithfulness): fixed UTC-5 contradicts the concept's own rules; its excess is summer days where '08:30' is the 09:30 cash open.",
    ("gap-direction-fade-rule", "a"): "Refuted (faithfulness): Sunday gaps were matched to quieter weekday reopens; a Sunday-only null cuts the Sunday effect from +16.8 to +3.2pp.",
    ("point-of-interest", "a"): None,
    ("fvg-three-levels", ""): None,
    ("trading-without-structure-shift", "a"): "Refuted (both): an unusually bad locked-seed control draw (3.8 SD) and block B2 only; the independent build is NULL.",
    ("deviation-close-continuation", "a"): "Refuted (both): a mirror target at the same distance is hit as often - volatility after a strong close, not continuation.",
    ("no-fading-the-daily-candle", "a"): "Refuted (both): depends on the locked control draw: six other seeds give +0.017 to +0.032 (mean +0.025) against +0.031 reported, at the edge of significance.",
    ("no-fading-the-daily-candle", "b"): "Refuted (faithfulness): its distinguishing small-wick test does nothing (-0.012R); knife-edge wick cut.",
    ("intraday-reversal", ""): "Verifiers upheld (+3.4pp that the 4H C2 + 1H CISD extreme holds the day; stronger on the futures grid) but BH q=0.11 - candidate only.",
    ("average-daily-range", "a"): "Refuted (both): the 'range covered' complement is a late-session set; ToD-matched control gives NULL (+0.024 [-0.010,+0.057]).",
    ("average-daily-range", "b"): "Refuted (both): same time-of-day confound as reading a; NULL under the ToD-matched control.",
    ("failure-to-displace", "a"): "Refuted (faithfulness): the gain is in stops under $0.30 in 2016-18 (microstructure); without them NULL.",
    ("aggressive-run-hammer-signature", ""): None,
    ("cheat-code-entry", ""): None,
}

COLS = ["concept_id", "reading", "category", "voice", "test_type", "verdict", "n", "diff", "ci_lo", "ci_hi",
        "p", "q_bh", "holm", "verified", "deepdive_label", "summary", "result_path", "script"]


def one_line(s, limit=320):
    s = re.sub(r"\s+", " ", s or "").strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    m = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[:m + 1] if m > 120 else cut.rstrip() + "…").strip()


def fnum(x, nd=6):
    if x is None:
        return ""
    if isinstance(x, bool):
        return str(x)
    return f"{x:.{nd}g}" if isinstance(x, float) else str(x)


def main():
    batches = load("batches.json")
    meta = {c: (b["category"], b["voice"]) for b in batches for c in b["concepts"]}
    raw = load("campaign_raw.json")
    adj = {x["file"]: x for x in load("campaign_adjusted.json")}
    ver = {(v["concept_id"], v["reading"] or ""): v for v in raw["verification"]}

    rows = []
    for r in raw["rows"]:
        f = os.path.basename(r["result_path"])
        if not f.endswith(".json"):  # two tester rows put the script path in result_path
            f = f"{r['concept_id']}__{r['reading']}.json" if r.get("reading") else f"{r['concept_id']}.json"
        a = adj[f]
        res = json.load(open(os.path.join(HERE, "results", f)))
        rd = a["reading"] or ""
        key = (r["concept_id"], rd)
        cat, voice = meta[r["concept_id"]]
        v = ver.get(key)
        if v is None:
            verified = ""
        elif v["survives"]:
            verified = "upheld"
        else:
            lenses = [x["lens"] for x in v["votes"] if x["refuted"]]
            verified = "refuted_both" if len(lenses) == 2 else f"refuted_{lenses[0]}"
        dd = DEEPDIVE.get(r["concept_id"]) if (verified == "upheld" and a["p_bh_reject"]) else None
        if dd:
            summary = dd[1]
        elif key in EDGE_NOTES and EDGE_NOTES[key]:
            summary = EDGE_NOTES[key]
        else:
            summary = one_line(r["summary"])
        tested = a["p"] is not None
        rows.append({
            "concept_id": r["concept_id"], "reading": rd, "category": cat, "voice": voice,
            "test_type": a["test_type"], "verdict": a["verdict"], "n": fnum(a["n"]),
            "diff": fnum(a["diff"]), "ci_lo": fnum(a["ci_lo"]), "ci_hi": fnum(a["ci_hi"]),
            "p": fnum(a["p"], 4), "q_bh": fnum(a["q_bh"], 4) if tested else "",
            "holm": ("reject" if a["p_holm_reject"] else "keep") if tested else "",
            "verified": verified, "deepdive_label": dd[0] if dd else "", "summary": summary,
            "result_path": f"concept_campaign/results/{f}",
            "script": os.path.relpath(res["script"], os.path.dirname(HERE)) if res.get("script") else "",
        })
    missing = [k for k in ver if k not in EDGE_NOTES]
    assert not missing, f"verified EDGE without a post-verification note: {missing}"
    rows.sort(key=lambda x: (x["concept_id"], x["reading"]))
    out = os.path.join(HERE, "concept_verdicts.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    # ---- headline counts ------------------------------------------------------------
    print(f"wrote {len(rows)} rows ({len({r['concept_id'] for r in rows})} concepts) to {out}")
    V = ["EDGE", "NEGATIVE", "NULL", "UNDERPOWERED", "UNTESTABLE"]
    pr = {"EDGE": 0, "NEGATIVE": 1, "NULL": 2, "UNDERPOWERED": 3, "UNTESTABLE": 4}
    concept = {}
    for r in rows:
        c = r["concept_id"]
        if c not in concept or pr[r["verdict"]] < pr[concept[c]["verdict"]]:
            concept[c] = r
    for level, items in (("readings", rows), ("concepts (best reading)", list(concept.values()))):
        print(f"\n== {level}: n={len(items)}")
        for dim in ("category", "voice"):
            t = collections.defaultdict(collections.Counter)
            for r in items:
                t[r[dim]][r["verdict"]] += 1
            print(f"{dim:10s} " + " ".join(f"{v:>12s}" for v in V) + "   total")
            for k in sorted(t):
                print(f"{k:10s} " + " ".join(f"{t[k][v]:12d}" for v in V) + f"   {sum(t[k].values())}")
            tot = collections.Counter(r["verdict"] for r in items)
            print(f"{'ALL':10s} " + " ".join(f"{tot[v]:12d}" for v in V) + f"   {len(items)}")


if __name__ == "__main__":
    main()
