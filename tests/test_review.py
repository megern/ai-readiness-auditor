from fastapi.testclient import TestClient
from app.main import app


def payload(score=5, evidence=None):
    return {
        "dimensions": {
            name: {"score": score, "evidence": evidence or []}
            for name in ["strategy", "data", "governance", "people", "infrastructure"]
        }
    }


def test_review_missing_evidence_caps_maximum():
    response = TestClient(app).post("/analyze", json=payload())
    assert response.status_code == 200
    assert response.json()["score_out_of_100"] == 20
    assert response.json()["band"] == "foundational"


def test_review_whitespace_is_not_evidence():
    response = TestClient(app).post("/analyze", json=payload(evidence=["   "]))
    assert response.json()["score_out_of_100"] == 20


def test_review_full_evidence_and_rejected_dimensions():
    client = TestClient(app)
    assert (
        client.post("/analyze", json=payload(evidence=["synthetic assertion"])).json()[
            "score_out_of_100"
        ]
        == 100
    )
    data = payload()
    data["dimensions"]["unexpected"] = {"score": 5}
    assert client.post("/analyze", json=data).status_code == 422
