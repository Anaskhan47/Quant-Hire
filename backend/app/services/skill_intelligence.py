import re
import logging
import json
import asyncio
import numpy as np
from typing import Dict, List, Set, Any, Tuple
from ..core.config import settings
from ..models.loader import model_loader
from .llm_service import llm_service
from ..schemas.predict import SkillDetail
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger("backend.skill_engine")

STRONG_KEYWORDS = ["deployed", "production", "scalable", "api", "real-time", "led", "architected", "optimized"]

class SkillIntelligenceEngine:
    def __init__(self):
        self.catalog: Set[str] = settings.SKILL_CATALOG

    def clean_text(self, text: str) -> str:
        if not isinstance(text, str): return ""
        text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", " ", text).lower()
        text = re.sub(r"[^a-z0-9\s#\+/]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def get_catalog_baseline(self, text: str) -> Dict[str, float]:
        """Maps each skill found in the text to its pre-defined importance weight."""
        clean = self.clean_text(text)
        found = {}
        for skill in self.catalog:
            if re.search(rf"\b{re.escape(skill)}\b", clean):
                found[skill] = settings.ALL_SKILL_WEIGHTS.get(skill, 0.7)
        return found

    async def get_unified_skill_graph(self, resume_text: str, jd_text: str) -> Tuple[List[SkillDetail], bool]:
        """Integrated Extraction with Precise Matching (Rule 2)."""
        jd_skills_map = self.get_catalog_baseline(jd_text)
        if not jd_skills_map:
             return [], True

        res_clean = self.clean_text(resume_text)
        
        # Build initial graph with deterministic strictness
        graph = []
        for name, imp in jd_skills_map.items():
            # RULE: if skill in text: accept (0.8) else: reject (0.0)
            # Semantic matching is handled in refinement or as part of fallback
            # Determinstic requirement check
            is_req = imp >= 1.5
            prof = 0.8 if re.search(rf"\b{re.escape(name)}\b", res_clean) else 0.0
            
            graph.append(SkillDetail(
                name=name,
                is_required=is_req,
                importance=imp, 
                proficiency=prof,
                contribution=round(imp * prof, 4)
            ))

        # 3. LLM Refinement (Constrained)
        try:
            refined = await llm_service.refine_skill_graph(resume_text, jd_text, graph)
            if refined:
                final_graph = []
                for s in refined:
                    orig = next((x for x in graph if x.name == s.name), None)
                    orig_prof = orig.proficiency if orig else 0.0
                    is_req = orig.is_required if orig else (s.importance >= 1.5)
                    
                    final_prof = s.proficiency
                    if orig_prof == 0.0 and s.proficiency < 0.6: 
                        final_prof = 0.0
                    
                    final_graph.append(SkillDetail(
                        name=s.name, 
                        is_required=is_req,
                        importance=s.importance, 
                        proficiency=final_prof, 
                        contribution=round(s.importance * final_prof, 4)
                    ))
                return final_graph, False
        except Exception as e:
            log.error(f"Refinement failure: {e}")
        
        return graph, True

    def get_embedding_score(self, r_text: str, j_text: str) -> Tuple[float, bool]:
        if not model_loader.emb_model: return 0.5, True
        r_c, j_c = self.clean_text(r_text), self.clean_text(j_text)
        if not r_c or not j_c: return 0.0, False
        try:
            r_emb = model_loader.emb_model.encode([r_c], normalize_embeddings=True)
            j_emb = model_loader.emb_model.encode([j_c], normalize_embeddings=True)
            return float(np.clip(np.dot(r_emb[0], j_emb[0]), 0.0, 1.0)), False
        except Exception: return 0.5, True

    def get_keyword_strength(self, r_text: str) -> float:
        clean = self.clean_text(r_text)
        matches = sum(1 for kw in STRONG_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", clean))
        return float(min(1.0, matches / len(STRONG_KEYWORDS)))

    def get_section_similarity(self, r_text: str, j_text: str) -> float:
        def isolate(text, section):
            pattern = rf"(?:{section})[^a-z]{{1,10}}(.*?)(?:experience|skills|projects|education|$)"
            m = re.search(pattern, self.clean_text(text), re.IGNORECASE | re.DOTALL)
            return m.group(1).strip() if m else ""
        r_s, j_s = isolate(r_text, "skills"), isolate(j_text, "skills")
        if not r_s or not j_s: return 0.0
        try:
            v = TfidfVectorizer(max_features=500); m = v.fit_transform([r_s, j_s])
            return float(cosine_similarity(m[0:1], m[1:2])[0][0])
        except Exception: return 0.0

    def extract_experience(self, text: str) -> int:
        nums = re.findall(r"(\d+)\+?\s*years?", self.clean_text(text))
        return max([int(n) for n in nums]) if nums else 0

skill_engine = SkillIntelligenceEngine()
