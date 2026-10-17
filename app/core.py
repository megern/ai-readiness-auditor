"""Explicit readiness rubric; scores are self-reported and evidence-weighted."""

from pydantic import BaseModel, Field, ConfigDict

RUBRIC = {
    "strategy": 0.20,
    "data": 0.25,
    "governance": 0.20,
    "people": 0.15,
    "infrastructure": 0.20,
}
ACTIONS = {
    "strategy": "Define measurable use cases and accountable owners.",
    "data": "Inventory data and establish quality and access controls.",
    "governance": "Document risk review, privacy controls and model approval.",
    "people": "Assign delivery roles and train practitioners.",
    "infrastructure": "Establish reproducible deployment and monitoring.",
}


class Dimension(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: float = Field(ge=0, le=5, allow_inf_nan=False)
    evidence: list[str] = Field(default_factory=list, max_length=20)


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimensions: dict[str, Dimension]


def analyze(request: Request) -> dict:
    if set(request.dimensions) != set(RUBRIC):
        raise ValueError("Supply exactly these dimensions: " + ", ".join(RUBRIC))
    details = []
    for name, weight in RUBRIC.items():
        item = request.dimensions[name]
        verified = any(e.strip() for e in item.evidence)
        adjusted = item.score if verified else min(item.score, 1.0)
        contribution = adjusted / 5 * weight * 100
        details.append(
            {
                "dimension": name,
                "weight": weight,
                "reported_score": item.score,
                "evidence_present": verified,
                "effective_score": adjusted,
                "contribution": round(contribution, 2),
                "priority": round((5 - adjusted) * weight, 3),
                "action": ACTIONS[name],
            }
        )
    total = round(sum(d["contribution"] for d in details), 2)
    return {
        "score_out_of_100": total,
        "band": "ready"
        if total >= 80
        else "developing"
        if total >= 50
        else "foundational",
        "dimensions": details,
        "prioritized_actions": sorted(
            [d for d in details if d["effective_score"] < 5],
            key=lambda d: (-d["priority"], d["dimension"]),
        ),
        "method": "Weighted score / 5; missing evidence caps dimension at 1. Evidence presence is not independently verified.",
    }


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline: Request
    current: Request


def compare(request: ComparisonRequest) -> dict:
    """Recompute both inputs against the fixed rubric; never trust exported totals."""
    baseline = analyze(request.baseline)
    current = analyze(request.current)
    changes = []
    for before, after in zip(baseline["dimensions"], current["dimensions"]):
        name = after["dimension"]
        old_evidence = {
            e.strip() for e in request.baseline.dimensions[name].evidence if e.strip()
        }
        new_evidence = {
            e.strip() for e in request.current.dimensions[name].evidence if e.strip()
        }
        changes.append(
            {
                "dimension": name,
                "weight": after["weight"],
                "baseline_reported_score": before["reported_score"],
                "current_reported_score": after["reported_score"],
                "baseline_effective_score": before["effective_score"],
                "current_effective_score": after["effective_score"],
                "baseline_contribution": before["contribution"],
                "current_contribution": after["contribution"],
                "weighted_score_delta": round(
                    after["contribution"] - before["contribution"], 2
                ),
                "baseline_evidence_present": before["evidence_present"],
                "current_evidence_present": after["evidence_present"],
                "evidence_added": sorted(new_evidence - old_evidence),
                "evidence_removed": sorted(old_evidence - new_evidence),
            }
        )
    current["comparison"] = {
        "baseline_score": baseline["score_out_of_100"],
        "current_score": current["score_out_of_100"],
        "total_delta": round(
            current["score_out_of_100"] - baseline["score_out_of_100"], 2
        ),
        "dimensions": changes,
        "method": "Both assessments are recomputed against the same fixed rubric. Evidence descriptions are trimmed and compared as sets; additions do not verify controls or establish certification.",
    }
    return current
