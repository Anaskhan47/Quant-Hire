from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Optional

class SkillDetail(BaseModel):
    name: str
    is_required: bool
    importance: float   
    proficiency: float  
    contribution: float 

class PredictRequest(BaseModel):
    resume: str = Field(..., min_length=1)
    job_description: str = Field(..., min_length=1)

class RoadmapStep(BaseModel):
    week: int
    skills: List[str]
    actions: List[str]

class FeatureTrace(BaseModel):
    keyword_alignment: float
    semantic_match: float
    experience_fit: float

class IntelligenceReport(BaseModel):
    insight: str
    strengths: List[str]
    weaknesses: List[str]
    verdict: str
    roadmap: List[RoadmapStep]

class ATSOptimization(BaseModel):
    current_score: float
    potential_score: float
    optimization_details: str

class PredictResponse(BaseModel):
    shortlist_probability: float = Field(..., ge=0.0, le=100.0)
    required_match: float = Field(..., ge=0.0, le=100.0)
    optional_match: float = Field(..., ge=0.0, le=100.0)
    skill_match: float = Field(..., ge=0.0, le=100.0)
    
    matched_skills: List[str]
    missing_skills: List[str]
    all_requirements_met: bool
    
    feature_trace: FeatureTrace
    intelligence_report: IntelligenceReport
    ats_optimization: Optional[str] = None
    
    request_id: str = "PROD-GEN-000"
    verdict: Optional[str] = None
    llm_insights: Optional[str] = None
    improvement_plan: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())
