"""LOCKED verdict rules for the 471-concept campaign.

Written 2026-09-23, BEFORE any concept was tested. Version 2 (same day, still before
any campaign result was written) adds the review fixes: clustered/time-block CIs and
an effective-n floor, the M1 tie-convention robustness rule, the control-overlap rule
and the write-time knob/probe locks (see "rules-2 additions" below). Nothing in this file may be
changed after the first result is written; `tests/test_rules_locked.py` pins every
constant, so a change fails the suite loudly instead of drifting silently. If a
rule turns out to be wrong, the fix is a NEW `RULES_VERSION` and a re-run of every
result, never an edit that only later concepts see.

Where a number already existed in the project it is IMPORTED, not re-typed, so the
campaign cannot drift from phase 3 (`backtest_conjunction.py`, §4.3 / §4.5).

The verdict is a pure function of numbers the harness computed. It never looks at
a raw win rate. Five labels, applied in this order:

  UNTESTABLE(reason)  the concept could not be operationalised on this data, or
                      the run tripped the harness sanity floor on a CI that
                      excludes zero (a suspected fault is not a finding), or n < 30.
  NEGATIVE            the CI on the differential excludes 0 AGAINST the claim.
  EDGE                the CI excludes 0 IN the claimed direction, AND both
                      calendar halves (2016-2020, 2021-end) have the claimed sign,
                      AND the test is powered (n >= power floor, i.e. MDE <= the
                      declared threshold, and n >= N_MIN_EDGE).
  NULL                the CI contains 0 AND the test is powered: an effect as
                      large as the threshold would have been detected, and was not.
  UNDERPOWERED        everything else: the CI contains 0 and MDE > threshold, or
                      the CI excludes 0 in the claimed direction but the halves
                      disagree or n is below the floor (`verdict_detail` says which).

Every result carries its raw two-sided p so the campaign applies Holm / BH across
all 471 concepts afterwards (`results.adjust_campaign`). A per-concept EDGE is
therefore a CANDIDATE until it survives that correction.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from backtest_conjunction import (CTRL_REPS, CTRL_WINDOW_DAYS, SEED, N_BOOT,  # noqa: F401
                                  BLOCK_MEAN, PRIMARY_COST, POWER_FLOOR_5PP,
                                  SANE_WIN, SANE_EXP_R, SANE_PF, SANE_DIFF_PP)

RULES_VERSION = "concept_lab-rules-2 (2026-09-23)"

# ── statistics ────────────────────────────────────────────────────────────────
ALPHA = 0.05                          # two-sided 95% CI
POWER = 0.80
Z_ALPHA = 1.959964
Z_POWER = 0.841621
MDE_Z = Z_ALPHA + Z_POWER             # 2.8016: MDE = MDE_Z * SE(diff)

# ── declared effect-size thresholds (the "would we have seen it" bar) ─────────
# A concept may only TIGHTEN these (declare a smaller threshold); loosening
# raises, because a looser threshold is the cheapest way to manufacture a NULL
# or an EDGE after the fact.
MDE_THRESHOLD_R = 0.10                # trade_test / gate_test, in R per trade
MDE_THRESHOLD_RATE_ABS = 0.05         # rate_test, absolute (5pp)
MDE_THRESHOLD_RATE_REL = 0.25         # rate_test, relative to the null rate
#   rate threshold = min(0.05, 0.25 * null_rate)

# ── sample floors ─────────────────────────────────────────────────────────────
N_MIN_ANY = 30                        # below this nothing is interpretable
N_MIN_EDGE = 200                      # absolute floor for EDGE / NULL, any test —
                                      # applied to n AND to the effective n (number
                                      # of independent clusters: trading days, or the
                                      # declared clusters), rules-2

# ── rules-2 additions (review of 2026-09-23) ──────────────────────────────────
# Dependence: CI = the WIDEST of i.i.d., event-block (mean 20 events), a stationary
# bootstrap over TRADING-DAY buckets (mean block = the book's own dependence
# length in days, >= 1) and, when declared, a bootstrap over explicit clusters.
DAY_BLOCK_RUN_QUANTILE = 0.90         # dependence length = max_hold + this quantile
                                      # of the same-direction overlapping-run length
# M1 tie convention: when the real and control arms differ in their share of
# ambiguous same-bar stop+target exits by more than this, the verdict must survive
# re-scoring every ambiguous bar as a 50/50 coin flip, or it is UNTESTABLE.
TIE_SHARE_TOL = 0.02
# Control overlap: when more than this share of control draws enter on the SAME M1
# bar, in the same direction, as one of the concept's own trades, the control is
# largely the concept itself and the differential is attenuated toward 0 — a NULL
# is then not evidence of absence (downgraded to UNDERPOWERED).
CTRL_OVERLAP_MAX = 0.20
# Behavioural lookahead probe required by write_result for every tested result.
PROBE_MIN_CUTS = 100                  # random cut points (symmetric set check)
PROBE_MIN_TARGETED = 20               # cuts at sampled decision times
# Knobs a written result must carry at their locked value (write_result refuses
# otherwise), and knobs that may differ from the default only when declared in
# params_source before the run. (`cluster` and `outcome_horizon` need no
# declaration: they only ADD a CI component, and the widest is used.)
LOCKED_KNOBS = {"seed": SEED, "n_boot": N_BOOT, "reps": CTRL_REPS,
                "window_days": CTRL_WINDOW_DAYS, "entry_mode": "next_open"}
DECLARABLE_KNOBS = {"ctrl_grid": "auto", "ctrl_tod_tol_min": None, "hold_basis": "clock",
                    "cost": PRIMARY_COST, "mde_threshold": None}

# ── time split (settled: the certified span starts 2016-01-01) ────────────────
SPLIT_DATE = pd.Timestamp("2021-01-01", tz="UTC")   # H1 = 2016-2020, H2 = 2021-end

# ── verdict labels ────────────────────────────────────────────────────────────
EDGE, NEGATIVE, NULL, UNDERPOWERED, UNTESTABLE = (
    "EDGE", "NEGATIVE", "NULL", "UNDERPOWERED", "UNTESTABLE")
VERDICTS = (EDGE, NEGATIVE, NULL, UNDERPOWERED, UNTESTABLE)
TEST_TYPES = ("trade", "gate", "rate", "untestable")


def mde_from_ci(lo: float, hi: float) -> float:
    """Minimum detectable effect (80% power, 5% two-sided) implied by a 95% CI."""
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return float("nan")
    se = (hi - lo) / (2 * Z_ALPHA)
    return float(MDE_Z * se)


def p_from_ci(obs: float, lo: float, hi: float) -> float:
    """Two-sided p from the (symmetric-normal) reading of the reported CI.

    Same convention as `backtest_conjunction.ci_p`, so campaign p-values and
    phase-3 p-values are on one scale.
    """
    if not all(np.isfinite(v) for v in (obs, lo, hi)):
        return float("nan")
    se = (hi - lo) / (2 * Z_ALPHA)
    if se <= 0:
        return float("nan")
    return float(math.erfc(abs(obs) / se / math.sqrt(2)))


def power_floor_n(n: int, mde: float, threshold: float) -> int:
    """n at which this test's MDE would equal `threshold` (MDE ~ 1/sqrt(n))."""
    if not (np.isfinite(mde) and n > 0 and threshold > 0):
        return int(10 ** 9)
    need = n * (mde / threshold) ** 2
    return int(max(N_MIN_EDGE, math.ceil(need)))


def resolve_threshold(test_type: str, declared: float | None,
                      null_rate: float | None = None) -> float:
    """The locked default threshold, or a declared TIGHTER one."""
    if test_type in ("trade", "gate"):
        default = MDE_THRESHOLD_R
    elif test_type == "rate":
        nr = null_rate if (null_rate is not None and np.isfinite(null_rate)) else 1.0
        base = min(nr, 1 - nr) if 0 < nr < 1 else nr
        default = min(MDE_THRESHOLD_RATE_ABS, MDE_THRESHOLD_RATE_REL * max(base, 1e-9))
    else:
        raise ValueError(f"unknown test_type {test_type!r}")
    if declared is None:
        return float(default)
    if declared > default + 1e-12:
        raise ValueError(
            f"mde_threshold {declared} is LOOSER than the locked default {default:.4f} "
            f"for a {test_type} test; thresholds may only be tightened (rules.py)")
    if declared <= 0:
        raise ValueError("mde_threshold must be > 0")
    return float(declared)


def verdict(*, diff: float, ci_lo: float, ci_hi: float, n: int,
            halves: dict | None, mde: float, mde_threshold: float,
            claim: str = "+", sanity_flags: list | None = None,
            testable: bool = True, untestable_reason: str | None = None,
            n_other: int | None = None, n_eff: int | None = None,
            ctrl_overlap: float | None = None) -> tuple[str, str]:
    """THE verdict. Returns (label, detail). Pure; see module docstring.

    `claim` is '+' when the concept claims the differential is positive (better
    trades, higher hit rate, gated beats complement) and '-' when it claims the
    opposite (e.g. "do not trade X" — gated trades should be WORSE).
    `n_other` is the smaller comparison arm for gate tests (the complement).
    `n_eff` (rules-2) is the effective sample size — the number of independent
    clusters (trading days / declared clusters; for gate tests the smaller arm's).
    It must also reach N_MIN_EDGE for EDGE or NULL.
    `ctrl_overlap` (rules-2): share of control draws that ARE one of the concept's
    own trades (same entry bar, same direction). Above CTRL_OVERLAP_MAX a NULL is
    downgraded to UNDERPOWERED (attenuation toward 0 cannot fake an EDGE, but it
    can fake a NULL).
    """
    if claim not in ("+", "-"):
        raise ValueError("claim must be '+' or '-'")
    if not testable:
        return UNTESTABLE, (untestable_reason or "declared untestable")
    if n is None or n < N_MIN_ANY or (n_other is not None and n_other < N_MIN_ANY):
        return UNTESTABLE, f"n={n} (other arm {n_other}) below N_MIN_ANY={N_MIN_ANY}"
    if not (np.isfinite(ci_lo) and np.isfinite(ci_hi) and np.isfinite(diff)):
        return UNTESTABLE, "no finite CI"
    s = 1.0 if claim == "+" else -1.0
    lo_c, hi_c = sorted((s * ci_lo, s * ci_hi))      # CI in claim-oriented units
    floor = power_floor_n(n, mde, mde_threshold)
    n_arm = n if n_other is None else min(n, n_other)
    n_eff = n_arm if n_eff is None else min(n_arm, int(n_eff))
    powered = bool(np.isfinite(mde) and mde <= mde_threshold and n_eff >= N_MIN_EDGE)
    flags = list(sanity_flags or [])

    if lo_c > 0 or hi_c < 0:
        if flags:
            return UNTESTABLE, ("sanity floor tripped on a CI excluding zero — "
                                "suspected harness fault, not a finding: " + "; ".join(flags))
    if hi_c < 0:
        return NEGATIVE, f"CI excludes 0 against the claim ({claim})"
    if lo_c > 0:
        h_ok, h_txt = _halves_agree(halves, s)
        if not h_ok:
            return UNDERPOWERED, f"CI excludes 0 in claimed direction but halves disagree ({h_txt})"
        if not powered:
            return UNDERPOWERED, (f"CI excludes 0 in claimed direction but not powered: "
                                  f"n={n_arm}, effective n={n_eff}, MDE={mde:.4f} vs "
                                  f"{mde_threshold:.4f}, floor {N_MIN_EDGE}; power floor "
                                  f"n={floor}")
        return EDGE, f"CI excludes 0 in claimed direction; halves agree ({h_txt}); powered"
    if powered:
        if ctrl_overlap is not None and np.isfinite(ctrl_overlap) and \
                ctrl_overlap > CTRL_OVERLAP_MAX:
            return UNDERPOWERED, (f"CI contains 0 but {ctrl_overlap:.0%} of control draws "
                                  f"are the concept's own trades (> {CTRL_OVERLAP_MAX:.0%}): "
                                  f"the differential is attenuated, so NULL is not shown")
        return NULL, f"CI contains 0; powered (MDE {mde:.4f} <= {mde_threshold:.4f})"
    return UNDERPOWERED, (f"CI contains 0; MDE {mde:.4f} vs threshold {mde_threshold:.4f}, "
                          f"effective n {n_eff} (power floor n={floor}, have {n_arm})")


def _halves_agree(halves: dict | None, s: float) -> tuple[bool, str]:
    if not halves or "H1" not in halves or "H2" not in halves:
        return False, "halves missing"
    d1, d2 = halves["H1"].get("diff"), halves["H2"].get("diff")
    if d1 is None or d2 is None or not (np.isfinite(d1) and np.isfinite(d2)):
        return False, f"H1={d1}, H2={d2}"
    ok = (s * d1 > 0) and (s * d2 > 0)
    return ok, f"H1 {d1:+.4f}, H2 {d2:+.4f}"


def tie_robust(label: str, detail: str, label_5050: str | None, tie_real: float | None,
               tie_ctrl: float | None) -> tuple[str, str]:
    """rules-2: the M1 tie convention may not decide the verdict.

    `label` is the verdict under the locked stop-first convention; `label_5050` the
    verdict with every AMBIGUOUS same-bar stop+target exit re-scored as a coin flip
    (0.5 x stop R + 0.5 x target R) in BOTH arms. Applied only when the arms' tie
    shares differ by more than TIE_SHARE_TOL (otherwise the convention cancels).
    """
    if tie_real is None or tie_ctrl is None or label_5050 is None:
        return label, detail
    gap = abs(tie_real - tie_ctrl)
    if gap <= TIE_SHARE_TOL or label == label_5050:
        return label, detail
    return UNTESTABLE, (f"M1 tie convention decides the verdict: stop-first -> {label}, "
                        f"50/50 ambiguous bars -> {label_5050} (ambiguous-exit share real "
                        f"{tie_real:.1%} vs control {tie_ctrl:.1%}); sub-minute order "
                        f"unknown")
