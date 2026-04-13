import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def _sanitize_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


class AnalyzeRequest(BaseModel):
    resume: str = Field(..., min_length=30, max_length=20000)
    job_description: str = Field(..., min_length=30, max_length=20000)

    @field_validator("resume", "job_description")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = _sanitize_text(value)
        if not cleaned:
            raise ValueError("Input text cannot be empty.")
        return cleaned


class ScoreResponse(BaseModel):
    tfidf_score: float = Field(..., ge=0, le=100)
    embedding_score: float = Field(..., ge=0, le=100)
    skill_match: float = Field(..., ge=0, le=100)
    experience_score: float = Field(..., ge=0, le=100)
    final_score: float = Field(..., ge=0, le=100)
    probability: float = Field(..., ge=0, le=100)
    matched_skills: List[str]
    missing_skills: List[str]
    years_resume: int = Field(..., ge=0, le=60)
    years_required: int = Field(..., ge=0, le=60)


class LLMFeedback(BaseModel):
    verdict: str = Field(..., min_length=3, max_length=220)
    experience_assessment: str = Field(..., min_length=10, max_length=1200)
    full_analysis: str = Field(..., min_length=30, max_length=12000)
    improvement_recommendations: List[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    match_score: int = Field(..., ge=0, le=100)
    shortlist_probability: int = Field(..., ge=0, le=100)
    skill_match_pct: int = Field(..., ge=0, le=100)
    resume_quality_score: int = Field(..., ge=0, le=100)
    experience_years_resume: int = Field(..., ge=0, le=60)
    experience_years_required: int = Field(..., ge=0, le=60)
    matched_skills: List[str]
    missing_skills: List[str]
    features: dict
    verdict: str
    experience_assessment: str
    full_analysis: str


class HealthResponse(BaseModel):
    status: str
    service: str
    provider: Optional[str] = None
