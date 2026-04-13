import logging
import json
import asyncio
from typing import Dict, List, Optional, Any
from groq import AsyncGroq
from ..core.config import settings
from ..schemas.predict import SkillDetail

log = logging.getLogger("backend.llm")

class LLMService:
    def __init__(self, api_key: str):
        self._client = AsyncGroq(api_key=api_key)

    async def refine_skill_graph(self, resume: str, jd: str, initial_graph: List[SkillDetail]) -> List[SkillDetail]:
        """Refines proficiency mapping with strict contextual analysis."""
        if not initial_graph: return []
        
        # 🚨 Constraint: DO NOT INFER NEW SKILLS. Only evaluate provided list.
        skill_names = [s.name for s in initial_graph]
        
        system_prompt = "You are a recruitment intelligence engine. You ONLY output strict JSON. You NEVER hallucinate skills outside the provided list."
        user_prompt = f"""Evaluate 'proficiency' (0.0 to 1.0) and 'importance' (0.1 to 1.0) for this exact list of skills found in JD: {', '.join(skill_names)}.
        
        Rules:
        1. YOU MUST NOT add any skills outside the provided list.
        2. Proficiency is 0.0 if the resume provides zero evidence of that specific skill or close domain equivalent.
        3. Resume Evidence must be direct (years and project impact).
        
        Output JSON:
        {{
            "skills": [
                {{"name": "{skill_names[0]}", "importance": float, "proficiency": float}},
                ...
            ]
        }}
        
        Resume: {resume[:1500]}
        JD: {jd[:1000]}"""
        
        try:
            response = await self._client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}],
                model=settings.LLM_MODEL, temperature=0.0, response_format={ "type": "json_object" }, timeout=30.0
            )
            data = json.loads(response.choices[0].message.content.strip())
            llm_items = {item['name']: item for item in data.get('skills', [])}
            
            refined = []
            for s in initial_graph:
                nuance = llm_items.get(s.name, {})
                i = float(nuance.get("importance", s.importance))
                p = float(nuance.get("proficiency", s.proficiency))
                refined.append(SkillDetail(
                    name=s.name, 
                    is_required=s.is_required, 
                    importance=i, 
                    proficiency=p, 
                    contribution=round(i*p, 4)
                ))
            return refined
        except Exception as e:
            log.error(f"LLM Refinement failure: {e}")
            return initial_graph

    async def generate_narrative(self, score: float, graph: List[SkillDetail], matched: List[str], missing: List[str]) -> str:
        """Explains the match results using strict tone mapping based on score thresholds."""
        
        # 🛠️ TONE MAPPING (Rule 3)
        if score >= 75: tone, label = "enthusiastic but analytical", "strong fit"
        elif score >= 60: tone, label = "neutral/positive", "moderate fit"
        elif score >= 40: tone, label = "skeptical/neutral", "borderline fit"
        else: tone, label = "critical/direct", "weak fit"

        system_prompt = f"You are a deterministic recruiter analyzer. Your tone is {tone}. You MUST describe the candidate as a {label}."
        user_prompt = f"""Match Score: {score:.1f}% ({label})
        Matched Skills: {', '.join(matched)}
        Missing Skills: {', '.join(missing)}
        
        SPECIAL CONTEXT: 
        If the candidate has strong 'Backend/Infra' but missing 'Core ML' (Scikit-learn, Feature Engineering), state:
        "Candidate demonstrates strong backend engineering capabilities with partial exposure to machine learning systems, but lacks depth in core ML areas."
        
        STRICT GUIDELINES:
        1. NEVER contradict the score or the {label} designation.
        2. Explain the fit using EXACTLY the Matched/Missing skills provided.
        3. No exaggerations. No hallucinated skills.
        4. Max 3 sentences."""
        
        try:
            response = await self._client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}],
                model=settings.LLM_MODEL, temperature=0.0, max_tokens=250
            )
            return response.choices[0].message.content.strip()
        except Exception:
             return f"Final analysis confirms a {label} based on quantitative skill mapping."

    async def generate_intelligence_report(self, score: float, similarity: float, exp_delta: float, matched: List[str], missing: List[str]) -> Dict[str, Any]:
        """Generates a high-fidelity intelligence report using strict prompt engineering."""
        
        system_prompt = "You are an AI Recruiter Intelligence engine. Return STRICT JSON only. No text outside JSON."
        
        user_prompt = f"""
        ANALYSIS DATA:
        - Match Score: {score:.1f}
        - Semantic Similarity: {similarity:.2f}
        - Experience Delta: {exp_delta:.1f} years
        - Matched Skills: {', '.join(matched)}
        - Missing Skills: {', '.join(missing)}

        Rules:
        * Follow numeric rules exactly
        * Use only missing_skills in roadmap
        * No extra skills allowed
        * If match_score < 50 → verdict MUST be "Reject"
        * If experience_delta >= 80 → include "severe mismatch"
        * Roadmap must cover ALL missing_skills
        * No skill outside missing_skills allowed

        JSON schema:
        {{
        "insight": "string (3–5 sentences, must include score, similarity, experience delta)",
        "strengths": ["string"],
        "weaknesses": ["string"],
        "verdict": "Reject | Consider | Strong Hire",
        "roadmap": [
        {{
        "week": 1,
        "skills": ["skill1", "skill2"],
        "actions": ["action1", "action2"]
        }}
        ]
        }}
        """

        try:
            response = await self._client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}],
                model=settings.LLM_MODEL, temperature=0.0, response_format={ "type": "json_object" }
            )
            report = json.loads(response.choices[0].message.content.strip())
            return report
        except Exception as e:
            log.error(f"Intelligence Report failure: {e}")
            return {
                "insight": f"Analysis confirmed score {score:.1f} with {similarity:.1f} similarity.",
                "strengths": matched[:3],
                "weaknesses": missing[:3],
                "verdict": "Consider" if score >= 50 else "Reject",
                "roadmap": [{"week": 1, "skills": missing[:2], "actions": ["Focus on missing core competencies"]}]
            }

    async def generate_ats_optimization(self, missing_skills: List[str]) -> str:
        """Generates the ATS Optimization strict text snippet."""
        
        system_prompt = """You are an AI Recruiter inside an ATS system.

STRICT RULES:
- Do NOT use markdown symbols (#, *, **)
- Do NOT add any extra sections
- Do NOT modify or calculate ATS score
- Keep output minimal, clean, and professional"""

        user_prompt = f"""ONLY OUTPUT THE FOLLOWING:

ATS Optimization

Missing Factors
- List only the most important missing elements affecting ATS score

Improvement Actions (Score Impact)
- Each action must directly fix a missing factor
- Each action must include score impact in (+X) format
- Keep actions short, specific, and high-impact

IMPACT RULES:
+12 to +15 → critical skill gaps
+8 to +11 → important gaps
+5 to +7 → moderate gaps

Context: The candidate is missing these skills: {', '.join(missing_skills) if missing_skills else "None. Just state that the candidate has strong ATS alignment."}"""

        try:
            response = await self._client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}],
                model=settings.LLM_MODEL, temperature=0.0, max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"ATS Optimization failure: {e}")
            return "ATS Optimization\n\nMissing Factors\n- Unable to generate optimization details\n\nImprovement Actions (Score Impact)\n- Review core competencies (+0)"

llm_service = LLMService(api_key=settings.GROQ_API_KEY)
