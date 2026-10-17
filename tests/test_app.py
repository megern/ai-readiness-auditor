from fastapi.testclient import TestClient
from app.main import app
from app.core import analyze, Request

client = TestClient(app)


def payload(score=5, evidence=None):
    return {
        "dimensions": {
            name: {"score": score, "evidence": evidence or []}
            for name in ["strategy", "data", "governance", "people", "infrastructure"]
        }
    }


def test_missing_evidence_caps_score():
    result = analyze(Request(**payload()))
    assert result["score_out_of_100"] == 20
    assert result["band"] == "foundational"
    assert result["prioritized_actions"][0]["dimension"] == "data"


def test_full_evidence():
    result = client.post("/analyze", json=payload(evidence=["Synthetic policy"])).json()
    assert result["score_out_of_100"] == 100
    assert result["prioritized_actions"] == []


def test_rejects_invalid_score_and_missing_dimensions():
    assert client.post("/analyze", json=payload(6)).status_code == 422
    assert client.post("/analyze", json={"dimensions": {}}).status_code == 422


def test_whitespace_evidence_and_frontend():
    assert (
        client.post("/analyze", json=payload(evidence=[" "])).json()["score_out_of_100"]
        == 20
    )
    assert client.get("/health").json() == {"status": "ok"}
    assert "Run analysis" in client.get("/").text


def test_weights_and_thresholds():
    data = payload(3, ["Synthetic evidence"])
    result = client.post("/analyze", json=data).json()
    assert result["score_out_of_100"] == 60
    assert result["band"] == "developing"
    assert sum(d["weight"] for d in result["dimensions"]) == 1
    data["dimensions"]["data"]["score"] = 0
    assert client.post("/analyze", json=data).json()["score_out_of_100"] == 45
