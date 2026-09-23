"""The verdict rules are LOCKED before any concept is tested. These tests pin every
constant and every branch, so a change to rules.py fails loudly."""
import numpy as np
import pytest

from concept_lab import rules
from concept_lab.rules import verdict, EDGE, NEGATIVE, NULL, UNDERPOWERED, UNTESTABLE


def test_constants_pinned():
    assert rules.RULES_VERSION == "concept_lab-rules-2 (2026-09-23)"
    assert rules.ALPHA == 0.05 and rules.POWER == 0.80
    assert abs(rules.MDE_Z - 2.801585) < 1e-5
    assert rules.MDE_THRESHOLD_R == 0.10
    assert rules.MDE_THRESHOLD_RATE_ABS == 0.05
    assert rules.MDE_THRESHOLD_RATE_REL == 0.25
    assert rules.N_MIN_ANY == 30 and rules.N_MIN_EDGE == 200
    assert str(rules.SPLIT_DATE) == "2021-01-01 00:00:00+00:00"
    # imported from phase 3, not re-typed
    assert rules.CTRL_REPS == 5 and rules.CTRL_WINDOW_DAYS == 30
    assert rules.N_BOOT == 2000 and rules.BLOCK_MEAN == 20
    assert rules.PRIMARY_COST == "0.04R" and rules.SEED == 20260825
    # rules-2 additions
    assert rules.DAY_BLOCK_RUN_QUANTILE == 0.90
    assert rules.TIE_SHARE_TOL == 0.02 and rules.CTRL_OVERLAP_MAX == 0.20
    assert rules.PROBE_MIN_CUTS == 100 and rules.PROBE_MIN_TARGETED == 20
    assert rules.LOCKED_KNOBS == {"seed": 20260825, "n_boot": 2000, "reps": 5,
                                  "window_days": 30, "entry_mode": "next_open"}
    assert set(rules.DECLARABLE_KNOBS) == {"ctrl_grid", "ctrl_tod_tol_min", "hold_basis",
                                           "cost", "mde_threshold"}


H_POS = {"H1": {"diff": 0.05}, "H2": {"diff": 0.04}}
H_MIX = {"H1": {"diff": 0.05}, "H2": {"diff": -0.01}}
H_NEG = {"H1": {"diff": -0.05}, "H2": {"diff": -0.04}}


@pytest.mark.parametrize("kw,expect", [
    # EDGE: CI > 0, halves agree, powered
    (dict(diff=.05, ci_lo=.02, ci_hi=.08, n=2000, halves=H_POS, mde=.04), EDGE),
    # CI > 0 but halves disagree -> not EDGE
    (dict(diff=.05, ci_lo=.02, ci_hi=.08, n=2000, halves=H_MIX, mde=.04), UNDERPOWERED),
    # CI > 0 but MDE above threshold -> not EDGE
    (dict(diff=.30, ci_lo=.05, ci_hi=.55, n=150, halves=H_POS, mde=.35), UNDERPOWERED),
    # CI > 0, MDE fine, but n below N_MIN_EDGE
    (dict(diff=.05, ci_lo=.02, ci_hi=.08, n=150, halves=H_POS, mde=.04), UNDERPOWERED),
    # CI < 0 against a '+' claim -> NEGATIVE (no power requirement)
    (dict(diff=-.05, ci_lo=-.08, ci_hi=-.02, n=100, halves=H_NEG, mde=.2), NEGATIVE),
    # CI contains 0, powered -> NULL
    (dict(diff=.005, ci_lo=-.02, ci_hi=.03, n=5000, halves=H_POS, mde=.035), NULL),
    # CI contains 0, not powered -> UNDERPOWERED
    (dict(diff=.05, ci_lo=-.1, ci_hi=.2, n=400, halves=H_POS, mde=.4), UNDERPOWERED),
    # tiny n -> UNTESTABLE
    (dict(diff=.5, ci_lo=.1, ci_hi=.9, n=10, halves=H_POS, mde=.4), UNTESTABLE),
])
def test_verdict_branches(kw, expect):
    v, _ = verdict(mde_threshold=0.10, claim="+", **kw)
    assert v == expect


def test_claim_minus_flips_direction():
    v, _ = verdict(diff=-.05, ci_lo=-.08, ci_hi=-.02, n=2000, halves=H_NEG, mde=.04,
                   mde_threshold=.1, claim="-")
    assert v == EDGE
    v, _ = verdict(diff=.05, ci_lo=.02, ci_hi=.08, n=2000, halves=H_POS, mde=.04,
                   mde_threshold=.1, claim="-")
    assert v == NEGATIVE


def test_sanity_flags_block_a_finding():
    v, d = verdict(diff=.05, ci_lo=.02, ci_hi=.08, n=2000, halves=H_POS, mde=.04,
                   mde_threshold=.1, sanity_flags=["win rate 95% outside (0.1, 0.9)"])
    assert v == UNTESTABLE and "harness fault" in d


def test_untestable_passthrough():
    v, d = verdict(diff=np.nan, ci_lo=np.nan, ci_hi=np.nan, n=0, halves=None, mde=np.nan,
                   mde_threshold=.1, testable=False, untestable_reason="paywalled rule")
    assert (v, d) == (UNTESTABLE, "paywalled rule")


def test_threshold_can_only_tighten():
    assert rules.resolve_threshold("trade", None) == 0.10
    assert rules.resolve_threshold("trade", 0.05) == 0.05
    with pytest.raises(ValueError):
        rules.resolve_threshold("trade", 0.2)
    assert rules.resolve_threshold("rate", None, null_rate=0.5) == 0.05
    assert abs(rules.resolve_threshold("rate", None, null_rate=0.04) - 0.01) < 1e-12
    with pytest.raises(ValueError):
        rules.resolve_threshold("rate", 0.03, null_rate=0.04)


def test_mde_and_p_from_ci():
    lo, hi = -0.0196, 0.0196                     # se = 0.01
    assert abs(rules.mde_from_ci(lo, hi) - 0.028016) < 1e-4
    assert abs(rules.p_from_ci(0.0196, 0.0, 0.0392) - 0.05) < 1e-3
    # floor: MDE 0.2 at n=100 -> need 400 for MDE 0.1
    assert rules.power_floor_n(100, 0.2, 0.1) == 400


def test_effective_n_floor_blocks_edge_and_null():
    """rules-2: 5,000 trades on 150 trading days is 150 independent units."""
    v, d = verdict(diff=.05, ci_lo=.02, ci_hi=.08, n=5000, halves=H_POS, mde=.04,
                   mde_threshold=.1, n_eff=150)
    assert v == UNDERPOWERED and "effective n=150" in d
    v, _ = verdict(diff=.005, ci_lo=-.02, ci_hi=.03, n=5000, halves=H_POS, mde=.035,
                   mde_threshold=.1, n_eff=150)
    assert v == UNDERPOWERED
    v, _ = verdict(diff=.05, ci_lo=.02, ci_hi=.08, n=5000, halves=H_POS, mde=.04,
                   mde_threshold=.1, n_eff=250)
    assert v == EDGE


def test_control_overlap_downgrades_null_only():
    kw = dict(mde_threshold=.1, halves=H_POS, n=5000, n_eff=1000)
    v, d = verdict(diff=.005, ci_lo=-.02, ci_hi=.03, mde=.035, ctrl_overlap=0.35, **kw)
    assert v == UNDERPOWERED and "attenuated" in d
    v, _ = verdict(diff=.005, ci_lo=-.02, ci_hi=.03, mde=.035, ctrl_overlap=0.10, **kw)
    assert v == NULL
    v, _ = verdict(diff=.05, ci_lo=.02, ci_hi=.08, mde=.04, ctrl_overlap=0.35, **kw)
    assert v == EDGE              # attenuation toward 0 cannot manufacture an EDGE


def test_tie_robust_rule():
    tr = rules.tie_robust
    assert tr(EDGE, "x", NULL, 0.40, 0.10)[0] == UNTESTABLE          # convention decides
    assert tr(EDGE, "x", EDGE, 0.40, 0.10)[0] == EDGE                # survives 50/50
    assert tr(NEGATIVE, "x", NULL, 0.110, 0.100)[0] == NEGATIVE      # within tolerance
    assert tr(NEGATIVE, "x", None, 0.40, 0.10)[0] == NEGATIVE        # not computed
