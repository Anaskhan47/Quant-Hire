import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.services.scoring import scoring_pipeline


def _run(coro):
    """Helper to run async code in sync tests."""
    return asyncio.run(coro)


def _mock_llm_report():
    """Default mock return for LLM intelligence report."""
    return {
        "insight": "Mock analysis.",
        "strengths": ["python"],
        "weaknesses": [],
        "verdict": "Strong Production Fit",
        "roadmap": [],
    }


def test_scoring_returns_valid_range():
    with patch("app.services.scoring.llm_service.generate_intelligence_report", new_callable=AsyncMock, return_value=_mock_llm_report()), \
         patch("app.services.scoring.llm_service.generate_ats_optimization", new_callable=AsyncMock, return_value="ATS OK"):
        result = _run(scoring_pipeline.process_analysis(
            "Python developer with 5 years experience in FastAPI, AWS, Docker, SQL, NLP.",
            "Need Python engineer with 4 years experience, FastAPI, AWS, Docker and SQL.",
        ))
    assert 0 <= result["shortlist_probability"] <= 100
    assert 0 <= result["skill_match"] <= 100
    assert 0 <= result["required_match"] <= 100
    assert isinstance(result["matched_skills"], list)
    assert isinstance(result["missing_skills"], list)


def test_skill_matching_behavior():
    with patch("app.services.scoring.llm_service.generate_intelligence_report", new_callable=AsyncMock, return_value=_mock_llm_report()), \
         patch("app.services.scoring.llm_service.generate_ats_optimization", new_callable=AsyncMock, return_value="ATS OK"):
        result = _run(scoring_pipeline.process_analysis(
            "Experienced in Python, SQL, Docker.",
            "Must know Python, SQL, Docker, Kubernetes.",
        ))
    matched_lower = [s.lower() for s in result["matched_skills"]]
    missing_lower = [s.lower() for s in result["missing_skills"]]
    assert "python" in matched_lower
    assert "kubernetes" in missing_lower
