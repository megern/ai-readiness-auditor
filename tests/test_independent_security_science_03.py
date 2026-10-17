from fastapi.testclient import TestClient
from app.main import app
from app.core import RUBRIC


def test_independent_evidence_caps_and_weighted_comparison_are_recomputed():
    baseline = {
        "dimensions": {name: {"score": 4, "evidence": ["old"]} for name in RUBRIC}
    }
    current = {
        "dimensions": {name: {"score": 4, "evidence": ["old"]} for name in RUBRIC}
    }
    current["dimensions"]["data"] = {"score": 5, "evidence": [" new ", "new"]}
    current["dimensions"]["governance"] = {"score": 5, "evidence": ["   "]}
    response = TestClient(app).post(
        "/compare", json={"baseline": baseline, "current": current}
    )
    assert response.status_code == 200
    result = response.json()["comparison"]
    assert (
        result["baseline_score"] == 80
        and result["current_score"] == 73
        and result["total_delta"] == -7
    )
    assert sum(row["weighted_score_delta"] for row in result["dimensions"]) == -7
    data = next(row for row in result["dimensions"] if row["dimension"] == "data")
    assert data["evidence_added"] == ["new"] and data["evidence_removed"] == ["old"]
    governance = next(
        row for row in result["dimensions"] if row["dimension"] == "governance"
    )
    assert (
        governance["current_effective_score"] == 1
        and governance["weighted_score_delta"] == -12
    )


def test_independent_invalid_dimensions_and_forged_totals_cannot_replace_inputs():
    client = TestClient(app)
    assert (
        client.post(
            "/compare",
            json={"baseline": {"dimensions": {}}, "current": {"dimensions": {}}},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/compare",
            json={"baseline": {"score_out_of_100": 100}, "current": {"dimensions": {}}},
        ).status_code
        == 422
    )
