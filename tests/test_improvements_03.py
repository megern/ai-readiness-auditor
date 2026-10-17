from copy import deepcopy
from fastapi.testclient import TestClient
from app.main import app
from app.core import RUBRIC, Request, ComparisonRequest, compare

client = TestClient(app)


def assessment(score=3, evidence=None):
    return {
        "dimensions": {
            key: {"score": score, "evidence": evidence or []} for key in RUBRIC
        }
    }


def test_known_weighted_delta_and_evidence_changes():
    before = assessment(5)
    after = assessment(5)
    after["dimensions"]["data"]["evidence"] = [
        " Synthetic quality record ",
        "Synthetic quality record",
    ]
    result = compare(
        ComparisonRequest(baseline=Request(**before), current=Request(**after))
    )
    comparison = result["comparison"]
    assert comparison["baseline_score"] == 20
    assert comparison["current_score"] == 40
    assert comparison["total_delta"] == 20
    data = next(d for d in comparison["dimensions"] if d["dimension"] == "data")
    assert data["weighted_score_delta"] == 20
    assert data["evidence_added"] == ["Synthetic quality record"]
    assert data["baseline_effective_score"] == 1
    assert data["current_effective_score"] == 5


def test_comparison_decline_is_negative_and_preserves_inputs():
    before = assessment(4, ["  Approved plan  "])
    current = assessment(4, [" "])
    original = deepcopy(before)
    response = client.post("/compare", json={"baseline": before, "current": current})
    assert response.status_code == 200
    result = response.json()
    assert result["comparison"]["total_delta"] == -60
    assert result["comparison"]["dimensions"][0]["evidence_removed"] == [
        "Approved plan"
    ]
    assert before == original


def test_report_totals_cannot_override_fixed_rubric_and_missing_dimension_rejected():
    value = assessment()
    value["score_out_of_100"] = 999
    assert (
        client.post(
            "/compare", json={"baseline": value, "current": assessment()}
        ).status_code
        == 422
    )
    invalid = assessment()
    del invalid["dimensions"]["data"]
    assert (
        client.post(
            "/compare", json={"baseline": invalid, "current": assessment()}
        ).status_code
        == 422
    )
    current = assessment()
    current["dimensions"]["strategy"]["score"] = 6
    assert (
        client.post(
            "/compare", json={"baseline": assessment(), "current": current}
        ).status_code
        == 422
    )
