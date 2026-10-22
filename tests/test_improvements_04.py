import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.planner import PlanRequest, plan
from app.core import RUBRIC

client = TestClient(app)


def assessment(score=0, evidence=None):
    return {
        "dimensions": {d: {"score": score, "evidence": evidence or []} for d in RUBRIC}
    }


def task(name, dimension="data", target=2, effort=2, dependencies=None):
    return {
        "id": name,
        "dimension": dimension,
        "target_score": target,
        "effort": effort,
        "owner": "Synthetic owner",
        "evidence_commitment": "Synthetic proposed evidence",
        "prerequisites": dependencies or [],
    }


def test_recomputes_marginal_gain_after_each_selection():
    r = plan(
        PlanRequest(
            assessment=assessment(),
            tasks=[
                task("initial"),
                task("deeper", target=4, effort=5),
                task("people", "people"),
            ],
            effort_budget=9,
        )
    )
    assert [t["id"] for t in r["selected"]] == ["initial", "people", "deeper"]
    assert [t["marginal_weighted_gain"] for t in r["selected"]] == [10, 6, 10]
    assert (
        r["baseline_score"] == 0
        and r["projected_score"] == 26
        and r["effort_used"] == 9
    )
    assert r["unscheduled"] == []


def test_evidence_cap_baseline_and_projected_commitment_assumption():
    payload = {
        "assessment": assessment(5),
        "tasks": [task("evidence", target=5, effort=1)],
        "effort_budget": 1,
    }
    response = client.post("/plan", json=payload)
    assert response.status_code == 200
    r = response.json()
    assert r["baseline_score"] == 20 and r["projected_score"] == 40
    assert r["selected"][0]["marginal_weighted_gain"] == 20
    assert "assumed" in r["method"]


def test_zero_gain_prerequisite_can_unlock_task_budget_and_reasons():
    r = plan(
        PlanRequest(
            assessment=assessment(),
            tasks=[
                task("prereq", target=0, effort=1),
                task("child", target=5, effort=2, dependencies=["prereq"]),
                task("too-big", effort=9),
            ],
            effort_budget=3,
        )
    )
    assert [t["id"] for t in r["selected"]] == ["prereq", "child"]
    assert r["unscheduled"][0]["reason"] == "effort_budget"
    r = plan(
        PlanRequest(
            assessment=assessment(),
            tasks=[task("p", effort=2), task("c", dependencies=["p"])],
            effort_budget=0,
        )
    )
    assert {t["id"]: t["reason"] for t in r["unscheduled"]} == {
        "p": "effort_budget",
        "c": "prerequisites_not_selected",
    }


@pytest.mark.parametrize(
    "tasks",
    [
        [task("a"), task("a")],
        [task("a", dependencies=["missing"])],
        [task("a", dependencies=["b"]), task("b", dependencies=["a"])],
        [task("a", dependencies=["a"])],
        [task("a", dependencies=["b", "b"]), task("b")],
        [task(str(i)) for i in range(31)],
    ],
)
def test_invalid_task_graphs_return_422(tasks):
    assert (
        client.post(
            "/plan",
            json={"assessment": assessment(), "tasks": tasks, "effort_budget": 9},
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "change",
    [
        {"effort": 0},
        {"effort": -1},
        {"target_score": 6},
        {"owner": "   "},
        {"evidence_commitment": ""},
        {"dimension": "unknown"},
    ],
)
def test_invalid_proposals_rejected(change):
    assert (
        client.post(
            "/plan",
            json={
                "assessment": assessment(),
                "tasks": [{**task("a"), **change}],
                "effort_budget": 3,
            },
        ).status_code
        == 422
    )


def test_decimal_effort_budget_never_overspends_or_loses_exact_decimal_fit():
    r = plan(
        PlanRequest(
            assessment=assessment(),
            tasks=[task("a", effort=0.1), task("b", "people", effort=0.2)],
            effort_budget=0.3,
        )
    )
    assert (
        len(r["selected"]) == 2
        and r["effort_used"] == 0.3
        and r["effort_remaining"] == 0
    )
    r = plan(
        PlanRequest(
            assessment=assessment(),
            tasks=[task("a", effort=0.10000000001)],
            effort_budget=0.1,
        )
    )
    assert not r["selected"]
    assert (
        client.post(
            "/plan",
            json={
                "assessment": assessment(),
                "tasks": [task("a", effort=1e-320)],
                "effort_budget": 1,
            },
        ).status_code
        == 422
    )


def test_empty_scenario_uses_identical_fixed_rubric_rounding():
    current = assessment(1.111, ["Synthetic evidence"])
    r = plan(PlanRequest(assessment=current, tasks=[], effort_budget=0))
    assert r["projected_score"] == r["baseline_score"] and r["score_delta"] == 0
