"""Result persistence, schema validation, and campaign-level multiple testing.

One JSON file per (concept, reading):
    research/concept_campaign/results/<concept_id>[__<reading>].json

SCHEMA (every file; `null` where not applicable)
  concept_id          str   id from concept_campaign/batches.json
  reading             str|null  which operationalisation of a contested concept
  testable            bool
  test_type           "trade" | "gate" | "rate" | "untestable"
  claim               "+" | "-"   direction the concept claims for `diff`
  operationalization  {"rules": [ordered, exact, testable statements],
                       "params": {every parameter: value}, ...free extras}
  params_source       {param: "corpus: <video_id> '<<=15-word quote>'" |
                               "threshold_fits: ..." | "session_window_fit: ..." |
                               "declared-before-run: <why>"}
                      — every key of operationalization.params must appear here
  n                   trades / gated trades / observations
  span                {start, end, years}
  avg_R, avg_R_gross, win_rate, pf        (trade & gate tests; null for rate)
  observed_rate, null_rate, lift          (rate tests)
  control             stats of the matched control / null
  diff, ci_lo, ci_hi, ci_method, p        the verdict statistic, its 95% CI, raw two-sided p
  halves              {"H1": {n, diff, ci_lo, ci_hi, p, start, end}, "H2": {...}, "split"}
  blocks              the four calendar quarters (descriptive)
  mde, mde_threshold, power_floor_n
  verdict             EDGE | NEGATIVE | NULL | UNDERPOWERED | UNTESTABLE
  verdict_detail      why (for UNTESTABLE: the reason)
  sanity_flags        list[str]
  lookahead           the assert_no_lookahead summary + the probe_lookahead result (or
                      the no_detector declaration) — REQUIRED for tested results
  (rules-2 extras kept verbatim from the test result: ci_components, dependence,
   ties, ctrl_overlap, events_fp, run_id, hyp_key)
  settings            harness knobs used (hold, cost, reps, grids, seed ...)
  notes               str
  script              path of the script that produced it (must exist)
  runtime_sec         float
  rules_version, harness_version, data {file, certified span, m1 bars}, written_at
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
import re
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_conjunction import holm
from . import rules
from .data import RESULTS_DIR, CAMPAIGN_DIR, span as _span, PARQUET

SCHEMA_FIELDS = (
    "concept_id", "reading", "testable", "test_type", "claim", "operationalization",
    "params_source", "n", "span", "avg_R", "avg_R_gross", "win_rate", "pf",
    "observed_rate", "null_rate", "lift", "control", "diff", "ci_lo", "ci_hi",
    "ci_method", "p", "halves", "blocks", "mde", "mde_threshold", "power_floor_n",
    "verdict", "verdict_detail", "sanity_flags", "lookahead", "settings", "notes",
    "script", "runtime_sec", "rules_version", "harness_version", "data", "written_at",
)
_SOURCE_PREFIXES = ("corpus", "threshold_fits", "session_window_fit",
                    "declared-before-run", "method_spec", "phase3")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_READ_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _known_ids() -> set:
    p = CAMPAIGN_DIR / "batches.json"
    if not p.exists():
        return set()
    return {c for b in json.loads(p.read_text()) for c in b["concepts"]}


def _jsonable(x):
    if x is pd.NaT or (isinstance(x, float) and math.isnan(x)):
        return None
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items() if not str(k).startswith("_")}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        x = float(x)
        return x if math.isfinite(x) else None
    if isinstance(x, (pd.Timestamp, pd.Timedelta, _dt.datetime, np.datetime64)):
        return str(x)
    if isinstance(x, (pd.DataFrame, pd.Series, np.ndarray)):
        raise TypeError("arrays/frames do not belong in a result file; summarise them")
    return x


def result_path(concept_id: str, reading: str | None = None,
                results_dir: Path | None = None) -> Path:
    d = Path(results_dir) if results_dir else RESULTS_DIR
    name = concept_id + (f"__{reading}" if reading else "")
    return d / f"{name}.json"


def validate_result(doc: dict, allow_unknown_id: bool = False) -> list[str]:
    """Return a list of schema problems (empty = valid)."""
    errs = []
    for k in SCHEMA_FIELDS:
        if k not in doc:
            errs.append(f"missing field {k}")
    cid = doc.get("concept_id")
    if not isinstance(cid, str) or not _ID_RE.match(cid or ""):
        errs.append(f"bad concept_id {cid!r}")
    elif not allow_unknown_id and _known_ids() and cid not in _known_ids():
        errs.append(f"concept_id {cid!r} not in concept_campaign/batches.json")
    rd = doc.get("reading")
    if rd is not None and not _READ_RE.match(str(rd)):
        errs.append(f"bad reading {rd!r} (letters, digits, _ . -)")
    if doc.get("test_type") not in rules.TEST_TYPES:
        errs.append(f"bad test_type {doc.get('test_type')!r}")
    if doc.get("verdict") not in rules.VERDICTS:
        errs.append(f"bad verdict {doc.get('verdict')!r}")
    op = doc.get("operationalization")
    if not isinstance(op, dict) or "rules" not in op or "params" not in op:
        errs.append("operationalization must be {'rules': [...], 'params': {...}}")
    else:
        if not op["rules"] or not isinstance(op["rules"], list):
            errs.append("operationalization.rules must be a non-empty list")
        ps = doc.get("params_source")
        if not isinstance(ps, dict):
            errs.append("params_source must be a dict {param: source}")
        else:
            for p in op["params"]:
                if p not in ps:
                    errs.append(f"param {p!r} has no params_source entry")
            for p, s in ps.items():
                if not isinstance(s, str) or not s.startswith(_SOURCE_PREFIXES):
                    errs.append(f"params_source[{p!r}] must start with one of "
                                f"{_SOURCE_PREFIXES}")
    if doc.get("testable"):
        if doc.get("test_type") == "untestable":
            errs.append("testable=True but test_type='untestable'")
        if doc.get("verdict") != rules.UNTESTABLE and doc.get("p") is None:
            errs.append("a tested result must carry its raw p")
    else:
        if doc.get("verdict") != rules.UNTESTABLE:
            errs.append("testable=False requires verdict UNTESTABLE")
        if not doc.get("verdict_detail"):
            errs.append("UNTESTABLE needs a reason in verdict_detail")
    scr = doc.get("script")
    if not scr or not Path(scr).exists():
        errs.append(f"script {scr!r} does not exist")
    return errs


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _gate_checks(result: dict, operationalization: dict, params_source: dict,
                 probe: dict | None, no_detector: str | None) -> list[str]:
    """rules-2 write-time locks for a TESTED result. Returns refusal reasons."""
    errs = []
    tt = result.get("test_type")
    st = result.get("settings") or {}
    # 1. locked knobs (no seed / reps / window re-rolls) ...
    for k, v in rules.LOCKED_KNOBS.items():
        if k in st and st[k] != v and not (k == "reps" and tt == "rate"
                                           and st.get("null_kind", "").startswith("analytic")):
            errs.append(f"setting {k}={st[k]!r} is locked to {v!r} for a written result "
                        f"(re-rolling it is a forking path)")
    # 2. ... and declarable knobs must be declared before the run
    for k, v in rules.DECLARABLE_KNOBS.items():
        if k in st and st[k] is not None and str(st[k]) != str(v) and k not in params_source:
            errs.append(f"non-default {k}={st[k]!r} needs a params_source entry "
                        f"('declared-before-run: ...' etc.)")
    # 3. the run must be in the ledger (so unwritten readings are counted)
    if not result.get("run_id"):
        errs.append("result has no run_id — the run ledger was disabled; rerun with it on")
    # 4. lookahead probe
    if probe is not None and not probe.get("passed"):
        errs.append(f"lookahead probe FAILED ({probe.get('failures')} cuts) — never written")
    if probe is None and not no_detector:
        errs.append("no probe_lookahead result: pass probe=cl.probe_lookahead(detect, "
                    "events) on the SAME frame you tested, or no_detector='<why the rule "
                    "is a pure clock/level rule with no detector>'")
    if probe is not None and probe.get("passed"):
        if not probe.get("symmetric"):
            errs.append("probe is from the old one-way probe; rerun probe_lookahead")
        if probe.get("events_fp") != result.get("events_fp"):
            errs.append("probe checked a different events frame than the one tested "
                        "(fingerprints differ) — probe and test the same frame")
        if (probe.get("n_cuts") or 0) < rules.PROBE_MIN_CUTS:
            errs.append(f"probe used {probe.get('n_cuts')} random cuts < "
                        f"{rules.PROBE_MIN_CUTS}")
        n_ev = result.get("n_events_in", result.get("n")) or 0
        if (probe.get("n_targeted") or 0) < min(rules.PROBE_MIN_TARGETED, n_ev):
            errs.append(f"probe sampled {probe.get('n_targeted')} decision times < "
                        f"{rules.PROBE_MIN_TARGETED}")
        if tt == "gate" and not result.get("mask_col"):
            errs.append("gate mask was passed as an array, so the probe never saw it: put "
                        "it in the events frame as a column, pass mask='<col>', and probe "
                        "that frame (or declare no_detector for a pure clock gate)")
        if tt == "gate" and result.get("mask_col") and \
                result["mask_col"] not in (probe.get("columns") or []):
            errs.append(f"probe did not compare the mask column {result['mask_col']!r}")
        if tt == "rate" and not result.get("predictors_probed"):
            errs.append("rate_test was run without predictors=<the probed frame>")
    return errs


def write_result(concept_id: str, reading: str | None, result: dict, *,
                 operationalization: dict, params_source: dict, script: str,
                 notes: str = "", probe: dict | None = None,
                 no_detector: str | None = None,
                 results_dir: Path | None = None, allow_unknown_id: bool = False,
                 m1=None) -> Path:
    """Validate and write one result. `result` is what a *_test returned.

    Refuses (ValueError) rather than writing an invalid file. Returns the path.
    For a tested result (rules-2) it also refuses unless: the probe passed on the
    very frame that was tested (fingerprint match, >= PROBE_MIN_CUTS random cuts,
    gate masks as probed columns, rate predictors probed) — or `no_detector`
    declares a pure clock/level rule; the locked knobs (seed, n_boot, reps,
    window_days, entry_mode) are at their locked values; any other non-default
    knob has a params_source entry; the run is in the ledger.
    """
    from . import HARNESS_VERSION
    doc = {k: None for k in SCHEMA_FIELDS}
    doc.update({k: v for k, v in result.items() if not k.startswith("_")})
    doc.update({
        "concept_id": concept_id, "reading": reading,
        "testable": result.get("test_type") != "untestable",
        "operationalization": operationalization, "params_source": params_source,
        "notes": notes, "script": str(Path(script).resolve()),
        "rules_version": rules.RULES_VERSION, "harness_version": HARNESS_VERSION,
        "data": {"file": str(PARQUET), **_span(m1)},
        "written_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    })
    if probe is not None:
        doc["lookahead"] = {**(doc.get("lookahead") or {}), "probe": probe}
    if no_detector:
        doc["lookahead"] = {**(doc.get("lookahead") or {}),
                            "no_detector_declaration": str(no_detector)}
    doc = _jsonable(doc)
    errs = validate_result(doc, allow_unknown_id)
    if doc.get("testable"):
        if result.get("rules_version") != rules.RULES_VERSION:
            errs.append(f"result computed under {result.get('rules_version')!r}, not the "
                        f"current {rules.RULES_VERSION!r} — rerun the test")
        errs += _gate_checks(result, operationalization or {}, params_source or {},
                             probe, no_detector)
    if errs:
        raise ValueError("result not written — schema problems:\n  " + "\n  ".join(errs))
    path = result_path(concept_id, reading, results_dir)
    _atomic_write_text(path, json.dumps(doc, indent=1, sort_keys=False))
    return path


def write_untestable(concept_id: str, reason: str, *, reading: str | None = None,
                     operationalization: dict | None = None,
                     params_source: dict | None = None, script: str,
                     notes: str = "", results_dir: Path | None = None,
                     allow_unknown_id: bool = False) -> Path:
    """Record UNTESTABLE(reason): e.g. paywalled rule, psychology, needs data we lack."""
    op = operationalization or {"rules": ["not operationalisable: " + reason], "params": {}}
    res = {"test_type": "untestable", "verdict": rules.UNTESTABLE, "verdict_detail": reason,
           "claim": None, "n": 0}
    return write_result(concept_id, reading, res, operationalization=op,
                        params_source=params_source or {}, script=script, notes=notes,
                        results_dir=results_dir, allow_unknown_id=allow_unknown_id)


def load_results(results_dir: Path | None = None) -> pd.DataFrame:
    d = Path(results_dir) if results_dir else RESULTS_DIR
    rows = []
    for p in sorted(d.glob("*.json")):
        doc = json.loads(p.read_text())
        rows.append({"file": p.name, **{k: doc.get(k) for k in (
            "concept_id", "reading", "test_type", "claim", "n", "diff", "ci_lo", "ci_hi",
            "p", "mde", "verdict", "verdict_detail", "hyp_key", "run_id")}})
    return pd.DataFrame(rows)


def load_ledger(path: str | Path | None = None) -> pd.DataFrame:
    """Every trade/gate/rate test call logged by the harness (one JSON per line)."""
    from .tests_api import LEDGER
    p = Path(path or os.environ.get("CONCEPT_LAB_LEDGER", LEDGER))
    if not p.exists():
        return pd.DataFrame()
    rows = []
    for line in p.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return pd.DataFrame(rows)


def adjust_campaign(results_dir: Path | None = None, alpha: float = 0.05,
                    ledger: str | Path | None | bool = None) -> pd.DataFrame:
    """Holm and Benjamini-Hochberg across every testable result's raw p — AND every
    hypothesis that was run but never written (rules-2).

    The family is: each written result, plus one entry per distinct `hyp_key` in
    the run ledger (test type, claim, events/mask fingerprints, settings except
    seed/n_boot) that no written result carries, at its most recent p. So a reading
    that was tried and dropped still costs multiplicity. `ledger=False` restricts
    the family to written results (diagnostic only).

    Adds `p_holm_reject`, `p_bh_reject`, `q_bh`; `df.attrs` carries `family_size`
    and `unwritten_hypotheses`. An EDGE that fails both is an EDGE candidate that
    did not survive the campaign's multiplicity. One-sided claims are not halved:
    p stays two-sided.
    """
    df = load_results(results_dir)
    extra = {}
    if ledger is not False:
        led = load_ledger(None if ledger in (None, True) else ledger)
        if not led.empty and "hyp_key" in led:
            written = set(df["hyp_key"].dropna()) if not df.empty and "hyp_key" in df else set()
            led = led[led["p"].notna() & ~led["hyp_key"].isin(written)]
            led = led.sort_values("time").groupby("hyp_key").tail(1)
            extra = {f"ledger:{k}": float(p) for k, p in zip(led["hyp_key"], led["p"])}
    if df.empty and not extra:
        return df
    ok = df["p"].notna() if not df.empty else pd.Series(dtype=bool)
    ps = {i: float(df.at[i, "p"]) for i in df.index[ok]} if not df.empty else {}
    fam = {**{("r", i): p for i, p in ps.items()}, **{("l", k): p for k, p in extra.items()}}
    hr = holm(fam, alpha)
    if df.empty:
        df = pd.DataFrame(columns=["concept_id", "p"])
    df["p_holm_reject"] = [hr.get(("r", i), False) for i in df.index]
    keys = list(fam.keys())
    pv = np.array([fam[k] for k in keys])
    q = np.full(len(df), np.nan)
    if len(pv):
        o = np.argsort(pv)
        m = len(pv)
        ranked = pv[o] * m / np.arange(1, m + 1)
        qq = np.minimum.accumulate(ranked[::-1])[::-1]
        qv = np.empty(m)
        qv[o] = np.minimum(qq, 1.0)
        for k, qk in zip(keys, qv):
            if k[0] == "r":
                q[df.index.get_loc(k[1])] = qk
    df["q_bh"] = q
    df["p_bh_reject"] = df["q_bh"] <= alpha
    df.attrs["family_size"] = len(fam)
    df.attrs["unwritten_hypotheses"] = len(extra)
    return df
