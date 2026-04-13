import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "system_status" in resp.json()

def test_metrics_endpoint():
    resp = client.get("/metrics")
    assert resp.status_code == 200

def test_predict_v2_endpoint_with_mocked_llm(monkeypatch):
    # Mocking the pipeline to return a PredictResponse dictionary 
    async def fake_process(resume, jd):
        return {
            "shortlist_probability": 85.0,
            "required_match": 100.0,
            "optional_match": 0.0,
            "skill_match": 80.0,
            "matched_skills": ["python", "aws"],
            "missing_skills": [],
            "all_requirements_met": True,
            "feature_trace": {
                "keyword_alignment": 80.0,
                "semantic_match": 85.0,
                "experience_fit": 90.0
            },
            "intelligence_report": {
                "insight": "Good fit.",
                "strengths": ["python"],
                "weaknesses": [],
                "verdict": "Strong Production Fit",
                "roadmap": []
            },
            "ats_optimization": "Optimized.",
            "request_id": "REQ-1234"
        }

    monkeypatch.setattr("app.main.scoring_pipeline.process_analysis", fake_process)
    
    payload = {
        "resume": "Python engineer with 5 years in FastAPI, Docker, AWS.",
        "job_description": "Need Python and FastAPI engineer with Docker and AWS experience."
    }
    resp = client.post("/v2/predict", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "shortlist_probability" in body
    assert "ats_optimization" in body

def test_predict_pdf_endpoint_with_mocked_pipeline(monkeypatch):
    async def fake_process(resume, jd):
        return {
            "shortlist_probability": 85.0,
            "required_match": 100.0,
            "optional_match": 0.0,
            "skill_match": 80.0,
            "matched_skills": ["python", "aws"],
            "missing_skills": [],
            "all_requirements_met": True,
            "feature_trace": {
                "keyword_alignment": 80.0,
                "semantic_match": 85.0,
                "experience_fit": 90.0
            },
            "intelligence_report": {
                "insight": "Good fit.",
                "strengths": ["python"],
                "weaknesses": [],
                "verdict": "Strong Production Fit",
                "roadmap": []
            },
            "ats_optimization": "Optimized.",
            "request_id": "REQ-1234"
        }

    monkeypatch.setattr("app.main.scoring_pipeline.process_analysis", fake_process)

    payload = {
        "job_description": "Need Python and FastAPI engineer with Docker and AWS experience."
    }
    files = {
        "resume_file": ("resume.txt", b"Python developer with 5 years in FastAPI, Docker, AWS, SQL.", "text/plain"),
    }
    resp = client.post("/predict-pdf", data=payload, files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert "shortlist_probability" in body
