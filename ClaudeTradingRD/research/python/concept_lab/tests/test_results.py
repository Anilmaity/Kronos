"""write_result schema, refusal on invalid input, UNTESTABLE records, campaign
multiple-testing adjustment."""
import json

import numpy as np
import pytest

import concept_lab as cl
from conftest import event_positions, events_at

OP = {"rules": ["enter long at the 14:00 UTC bar close", "stop 2.0, target 1R"],
      "params": {"stop_dist": 2.0, "rr": 1.0, "max_hold": "90min"}}
SRC = {"stop_dist": "declared-before-run: fixed synthetic geometry",
       "rr": "declared-before-run: 1R", "max_hold": "declared-before-run: 90 min"}


@pytest.fixture(scope="module")
def a_result(flat_m1):
    pos = event_positions(flat_m1, 400, seed=31)
    return cl.trade_test(events_at(flat_m1, pos, 1), max_hold="90min", m1=flat_m1,
                         keep_trades=True)


NODET = "pure clock rule: every 14:00 UTC bar close, fixed geometry"


def test_write_and_read_back(a_result, tmp_results, flat_m1):
    p = cl.write_result("cisd", "unit_test", a_result, operationalization=OP,
                        params_source=SRC, script=__file__, results_dir=tmp_results,
                        m1=flat_m1, no_detector=NODET)
    assert p.name == "cisd__unit_test.json"
    doc = json.loads(p.read_text())
    for k in cl.SCHEMA_FIELDS:
        assert k in doc
    assert "_trades" not in doc and doc["testable"] is True
    assert doc["verdict"] in cl.rules.VERDICTS and doc["p"] is not None
    assert doc["rules_version"] == cl.RULES_VERSION
    assert doc["run_id"] and doc["events_fp"] and doc["ci_components"]
    assert doc["lookahead"]["no_detector_declaration"] == NODET
    assert not cl.validate_result(doc)


def test_refuses_missing_param_source(a_result, tmp_results, flat_m1):
    src = dict(SRC)
    src.pop("rr")
    with pytest.raises(ValueError, match="rr"):
        cl.write_result("cisd", None, a_result, operationalization=OP, params_source=src,
                        script=__file__, results_dir=tmp_results, m1=flat_m1,
                        no_detector=NODET)


def test_refuses_unknown_concept_and_bad_source(a_result, tmp_results, flat_m1):
    with pytest.raises(ValueError, match="batches.json"):
        cl.write_result("not-a-real-concept-xyz", None, a_result, operationalization=OP,
                        params_source=SRC, script=__file__, results_dir=tmp_results,
                        m1=flat_m1, no_detector=NODET)
    bad = dict(SRC, rr="because I like it")
    with pytest.raises(ValueError, match="params_source"):
        cl.write_result("cisd", None, a_result, operationalization=OP, params_source=bad,
                        script=__file__, results_dir=tmp_results, m1=flat_m1,
                        no_detector=NODET)


def test_untestable_record(tmp_results):
    p = cl.write_untestable("cisd", "paywalled C2/C3 conditions", reading="paywall",
                            script=__file__, results_dir=tmp_results)
    doc = json.loads(p.read_text())
    assert doc["verdict"] == "UNTESTABLE" and doc["testable"] is False
    assert doc["verdict_detail"] == "paywalled C2/C3 conditions"


def test_adjust_campaign(tmp_path):
    d = tmp_path / "res"
    d.mkdir()
    for i, p in enumerate([0.0001, 0.02, 0.04, 0.5, None]):
        (d / f"c{i}.json").write_text(json.dumps({"concept_id": f"c{i}", "p": p,
                                                  "verdict": "NULL"}))
    df = cl.adjust_campaign(d, ledger=False).set_index("concept_id")
    assert bool(df.loc["c0", "p_holm_reject"]) and not bool(df.loc["c1", "p_holm_reject"])
    assert df.loc["c0", "q_bh"] == pytest.approx(0.0004)
    assert df.loc["c2", "q_bh"] == pytest.approx(0.04 * 4 / 3)
    assert np.isnan(df.loc["c4", "q_bh"])
