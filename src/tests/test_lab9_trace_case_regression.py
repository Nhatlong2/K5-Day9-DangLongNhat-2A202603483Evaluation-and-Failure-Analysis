import pytest

pytestmark = pytest.mark.student


def test_c002_keeps_database_delay_before_quoting():
    from lab9.trace_case import investigate

    broken = investigate("seeded_regression", "C-002", 11)["trial"]
    fixed = investigate("fixed", "C-002", 11)["trial"]

    assert broken["events"][1]["payload"]["lookup_order"]["order"]["delay_days"] == 2
    assert broken["events"][2]["kind"] == "model_override"
    assert broken["events"][2]["payload"]["delay_days"] == 5
    assert broken["snapshot"]["refund_vnd"] == 20_000
    assert broken["lab8_pass"] is False

    assert fixed["events"][2]["kind"] == "quote"
    assert fixed["events"][2]["payload"]["amount_vnd"] == 0
    assert fixed["snapshot"]["refund_vnd"] == 0
    assert fixed["lab8_pass"] is True


@pytest.mark.parametrize(("shape", "claim", "expected"), [
    ("seeded_regression", "C-014", False),
    ("fixed", "C-008", True),
])
def test_reply_amount_follows_the_posted_ledger(shape, claim, expected):
    from pydantic_evals.evaluators import EvaluatorContext

    from lab9.graders import ReplyMatchesLedger
    from lab9.trace_case import investigate

    case = investigate(shape, claim, 11)
    ctx = EvaluatorContext(name=claim, inputs={}, metadata=None, expected_output=case["label"],
                           output=case["trial"], duration=0.0, _span_tree=None,
                           attributes={}, metrics={})
    assert ReplyMatchesLedger().evaluate(ctx).value is expected
