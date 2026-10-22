"""Deterministic, bounded scenario planning against the fixed self-report rubric."""

from typing import Literal
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from .core import Request, RUBRIC, analyze


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=80)
    dimension: Literal["strategy", "data", "governance", "people", "infrastructure"]
    target_score: float = Field(ge=0, le=5, allow_inf_nan=False)
    evidence_commitment: str = Field(min_length=1, max_length=2000)
    effort: float = Field(ge=0.000001, le=1000000, allow_inf_nan=False)
    owner: str = Field(min_length=1, max_length=200)
    prerequisites: list[str] = Field(default_factory=list, max_length=30)


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment: Request
    tasks: list[Task] = Field(max_length=30)
    effort_budget: float = Field(ge=0, le=1000000, allow_inf_nan=False)


def plan(request: PlanRequest):
    baseline = analyze(request.assessment)
    tasks = {t.id: t for t in request.tasks}
    if len(tasks) != len(request.tasks):
        raise ValueError("Task IDs must be unique")
    for t in tasks.values():
        if len(set(t.prerequisites)) != len(t.prerequisites):
            raise ValueError("Prerequisites must be unique")
        if any(p not in tasks for p in t.prerequisites):
            raise ValueError("Unknown prerequisite")
    visited = set()
    active = set()

    def visit(name):
        if name in active:
            raise ValueError("Task prerequisites contain a cycle")
        if name in visited:
            return
        active.add(name)
        for dep in tasks[name].prerequisites:
            visit(dep)
        active.remove(name)
        visited.add(name)

    for name in tasks:
        visit(name)
    state = {d["dimension"]: d["effective_score"] for d in baseline["dimensions"]}
    selected = []
    done = set()
    remaining = Decimal(str(request.effort_budget))
    # Greedy marginal gain / effort is deliberately transparent, not a knapsack optimum.
    while True:
        candidates = []
        for t in tasks.values():
            if (
                t.id in done
                or not set(t.prerequisites) <= done
                or Decimal(str(t.effort)) > remaining
            ):
                continue
            gain = (
                max(
                    Decimal(0),
                    Decimal(str(t.target_score)) - Decimal(str(state[t.dimension])),
                )
                * Decimal(str(RUBRIC[t.dimension]))
                * 20
            )
            candidates.append((gain / Decimal(str(t.effort)), t.id, t, gain))
        if not candidates:
            break
        _, _, task, gain = sorted(candidates, key=lambda x: (-x[0], x[1]))[0]
        before = state[task.dimension]
        state[task.dimension] = max(before, task.target_score)
        remaining -= Decimal(str(task.effort))
        done.add(task.id)
        selected.append(
            {
                **task.model_dump(),
                "selection_order": len(selected) + 1,
                "effective_before": before,
                "effective_after": state[task.dimension],
                "marginal_weighted_gain": round(float(gain), 8),
                "gain_per_effort": round(float(gain / Decimal(str(task.effort))), 8),
            }
        )
    unscheduled = []
    for t in tasks.values():
        if t.id not in done:
            missing = [p for p in t.prerequisites if p not in done]
            unscheduled.append(
                {
                    "id": t.id,
                    "reason": "prerequisites_not_selected"
                    if missing
                    else "effort_budget",
                    "unselected_prerequisites": missing,
                    "effort": t.effort,
                }
            )
    projected = round(
        sum(round(score / 5 * RUBRIC[name] * 100, 2) for name, score in state.items()),
        2,
    )
    return {
        "baseline_score": baseline["score_out_of_100"],
        "projected_score": projected,
        "score_delta": round(projected - baseline["score_out_of_100"], 2),
        "effort_budget": request.effort_budget,
        "effort_used": float(Decimal(str(request.effort_budget)) - remaining),
        "effort_remaining": float(remaining),
        "selected": selected,
        "unscheduled": unscheduled,
        "projected_dimensions": state,
        "method": "Dependency-ready tasks ranked by current marginal weighted score gain / effort, ties by task ID. Gains recomputed after each selection. Zero-gain prerequisites can be selected. Greedy heuristic, not a globally optimal budget allocation. Proposed evidence is assumed delivered; no evidence verification, certification or ROI estimate.",
    }
