from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_task_workbench_and_bundled_assets():
    page = client.get("/")
    assert page.status_code == 200
    assert "Load synthetic example" in page.text
    assert "Export report" in page.text
    for path in ["/assets/app.js", "/assets/common.js", "/assets/styles.css", "/guide"]:
        assert client.get(path).status_code == 200
    assert "Intended use" in client.get("/guide").text
    assert app.version == "0.3.0"


def test_evidence_adjustment_is_reusable_questionnaire_payload():
    from app.core import RUBRIC

    data = {"dimensions": {name: {"score": 5, "evidence": ["   "]} for name in RUBRIC}}
    result = client.post("/analyze", json=data)
    assert result.status_code == 200
    assert result.json()["score_out_of_100"] == 20
    data["dimensions"]["data"]["evidence"] = ["Synthetic data quality checks"]
    result = client.post("/analyze", json=data).json()
    assert result["score_out_of_100"] == 40
    assert result["dimensions"][1]["effective_score"] == 5
