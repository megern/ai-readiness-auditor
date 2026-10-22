import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import RUBRIC

client = TestClient(app)


def assessment(score=1):
    return {
        "dimensions": {
            name: {"score": score, "evidence": ["self-reported evidence"]}
            for name in RUBRIC
        }
    }


def task(id, dimension, target, effort, prerequisites=None):
    return {
        "id": id,
        "dimension": dimension,
        "target_score": target,
        "effort": effort,
        "evidence_commitment": "Proposed evidence; not verified",
        "owner": "synthetic owner",
        "prerequisites": prerequisites or [],
    }


def test_decimal_budget_zero_gain_prerequisite_and_conditional_projection():
    payload = {
        "assessment": assessment(),
        "effort_budget": 0.3,
        "tasks": [
            task("prerequisite", "strategy", 1, 0.1),
            task("data-upgrade", "data", 3, 0.2, ["prerequisite"]),
        ],
    }
    response = client.post("/plan", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert [row["id"] for row in result["selected"]] == ["prerequisite", "data-upgrade"]
    assert result["effort_used"] == 0.3 and result["effort_remaining"] == 0
    assert (
        result["baseline_score"] == 20
        and result["projected_score"] == 30
        and result["score_delta"] == 10
    )
    assert result["selected"][0]["marginal_weighted_gain"] == 0
    assert payload["assessment"]["dimensions"]["data"]["score"] == 1


def test_marginal_gains_recomputed_after_overlapping_dimension_target():
    payload = {
        "assessment": assessment(0),
        "effort_budget": 6,
        "tasks": [
            task("data-two", "data", 2, 1),
            task("data-three", "data", 3, 3),
            task("strategy-one", "strategy", 1, 2),
        ],
    }
    result = client.post("/plan", json=payload).json()
    assert [row["id"] for row in result["selected"]] == [
        "data-two",
        "strategy-one",
        "data-three",
    ]
    assert [row["marginal_weighted_gain"] for row in result["selected"]] == [10, 4, 5]
    assert result["projected_score"] == 19
    payload = {
        "assessment": assessment(4),
        "effort_budget": 1,
        "tasks": [task("lower", "data", 2, 1)],
    }
    result = client.post("/plan", json=payload).json()
    assert result["projected_score"] == 80 and result["score_delta"] == 0


def test_missing_dependencies_cycles_and_blank_evidence_are_rejected():
    payload = {
        "assessment": assessment(),
        "effort_budget": 1,
        "tasks": [task("a", "data", 2, 0.1, ["unknown"])],
    }
    assert client.post("/plan", json=payload).status_code == 422
    payload["tasks"] = [
        task("a", "data", 2, 0.1, ["b"]),
        task("b", "data", 3, 0.1, ["a"]),
    ]
    assert client.post("/plan", json=payload).status_code == 422
    payload["tasks"] = [{**task("a", "data", 2, 0.1), "evidence_commitment": "  "}]
    assert client.post("/plan", json=payload).status_code == 422
