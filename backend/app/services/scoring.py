import logging
import asyncio
import numpy as np
import time
import json
import uuid
import math
import traceback
from typing import Dict, Any, List, Tuple
from ..core.config import settings
from ..core.metrics import metrics
from .skill_intelligence import skill_engine
from .llm_service import llm_service
from ..models.loader import model_loader
from ..schemas.predict import SkillDetail, PredictResponse, FeatureTrace

log = logging.getLogger("backend.production")

class ScoringPipeline:
    async def process_analysis(self, resume: str, jd: str) -> Dict[str, Any]:
        """Final Refactor: Strict Single Source of Truth for Pipeline Integrity."""
        request_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
        
        try:
            # Stage 1: Extraction Handshake
            log.info(json.dumps({"request_id": request_id, "checkpoint": "EXTRACTION_START"}))
            graph, llm_fallback = await skill_engine.get_unified_skill_graph(resume, jd)
            
            req_skills = [s for s in graph if s.is_required]
            weighted_sum = sum(s.proficiency * settings.ALL_SKILL_WEIGHTS.get(s.name, 0.4) for s in graph)
            total_possible_weight = sum(settings.ALL_SKILL_WEIGHTS.get(s.name, 0.4) for s in graph)
            
            final_skill_match = (weighted_sum / max(0.1, total_possible_weight)) * 100
            req_match_pct = (len([s for s in req_skills if s.proficiency >= 0.5]) / len(req_skills)) * 100 if req_skills else 100.0
            opt_match_pct = max(0.0, 100.0 - req_match_pct)
            
            emb_score, _ = await skill_engine.get_embedding_score(resume, jd)
            sect_score = skill_engine.get_section_similarity(resume, jd)
            keyword_score = skill_engine.get_keyword_strength(resume)
            exp_fit = min(1.0, skill_engine.extract_experience(resume) / max(1, skill_engine.extract_experience(jd)))
            
            log.info(json.dumps({"request_id": request_id, "checkpoint": "EXTRACTION_SUCCESS", "feature_count": 6}))

            # Stage 2: Feature Sanitization & Inference
            raw_features = [sect_score, emb_score, final_skill_match/100, exp_fit, keyword_score, sect_score]
            sanitized_features = [float(v) if (v is not None and not (isinstance(v, float) and np.isnan(v))) else 0.0 for v in raw_features]
            
            model_score = self._run_inference(sanitized_features)
            
            logit = (2.5 * model_score) + (1.5 * (final_skill_match/100.0)) - 2.0
            p_val = 1.0 / (1.0 + math.exp(-max(-20, min(20, logit)))) 
            shortlist_prob = round(max(0.0, min(p_val, 1.0)) * 100.0, 2)
            
            matched_names = [s.name for s in graph if s.proficiency >= 0.5]
            missing_names = [s.name for s in graph if s.proficiency < 0.2]
            
            matched_req = [s for s in req_skills if s.proficiency >= 0.5]
            all_req_met = len(matched_req) == len(req_skills)
            
            log.info(json.dumps({"rid": request_id, "step": "LLM_BINDING_START", "skills": len(graph)}))
            
            # Stage 3: LLM Contextual Binding (Hardened with Granular Fallbacks)
            try:
                # Calculate experience delta (absolute difference in years)
                resume_exp = skill_engine.extract_experience(resume)
                jd_exp = skill_engine.extract_experience(jd)
                exp_delta = abs(jd_exp - resume_exp)
                
                report_data, ats_optimization = await asyncio.gather(
                    llm_service.generate_intelligence_report(
                        score=shortlist_prob,
                        similarity=emb_score,
                        exp_delta=exp_delta,
                        matched=matched_names,
                        missing=missing_names
                    ),
                    llm_service.generate_ats_optimization(missing_names)
                )
            except Exception as e:
                log.warning(json.dumps({"rid": request_id, "msg": "LLM Failure", "error": str(e)}))
                ats_optimization = "ATS Optimization\n\nMissing Factors\n- System unavailable\n\nImprovement Actions (Score Impact)\n- Retry later (+0)"
                report_data = {
                    "insight": f"Quantitative analysis complete. Final alignment probability: {shortlist_prob}%.",
                    "strengths": matched_names[:3],
                    "weaknesses": missing_names[:3],
                    "verdict": self._get_verdict(shortlist_prob),
                    "roadmap": [{"week": 1, "skills": missing_names[:2], "actions": ["Focus on missing core competencies"]}]
                }

            log.info(json.dumps({"rid": request_id, "step": "PIPELINE_FINALIZED"}))

            return {
                "shortlist_probability": shortlist_prob,
                "required_match": round(req_match_pct, 2),
                "optional_match": round(opt_match_pct, 2),
                "skill_match": round(final_skill_match, 2),
                "matched_skills": matched_names,
                "missing_skills": missing_names,
                "all_requirements_met": all_req_met,
                "feature_trace": {
                    "keyword_alignment": round(keyword_score * 100, 2),
                    "semantic_match": round(emb_score * 100, 2),
                    "experience_fit": round(exp_fit * 100, 2)
                },
                "intelligence_report": report_data,
                "ats_optimization": ats_optimization,
                "verdict": report_data.get("verdict", "Candidate Processed"),
                "llm_insights": report_data.get("insight", "Analysis complete."),
                "improvement_plan": ats_optimization,
                "request_id": request_id
            }

        except Exception as e:
            trace = traceback.format_exc()
            log.critical(json.dumps({"rid": request_id, "error": str(e), "trace": trace}))
            raise

    def _run_inference(self, vector: List[float]) -> float:
        # Rigid Sanitization Bridge
        vector = [float(v) if (v is not None and not (isinstance(v, float) and np.isnan(v))) else 0.0 for v in vector]
        if not model_loader.ml_model or not hasattr(model_loader.ml_model, "predict_proba"):
             return float(np.mean(vector))
        try:
            probs = model_loader.ml_model.predict_proba(np.array([vector]))[0]
            return float(probs[1])
        except Exception:
            return float(np.mean(vector))

    def _get_verdict(self, prob: float) -> str:
        if prob >= 75: return "Strong Production Fit"
        if prob >= 60: return "Qualified Match"
        if prob >= 40: return "Borderline Potential"
        return "Low Strategic Alignment"

scoring_pipeline = ScoringPipeline()
