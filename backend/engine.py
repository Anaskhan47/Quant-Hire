import json
import os
import re
import logging
import traceback

log = logging.getLogger("recruitiq.engine")

# ✅ SSOT CONTRACT FIELDS
SSOT_FIELDS = {"experience_delta", "match_score", "verdict"}

# ✅ SKILL TYPE SYSTEM
SKILL_TYPES = {
    "scikit-learn": "ml", "tensorflow": "ml", "pytorch": "ml", "keras": "ml",
    "feature engineering": "ml", "xgboost": "ml", "lightgbm": "ml",
    "nlp": "ml", "computer vision": "ml", "llm": "ml", "rag": "ml",
    "aws": "cloud", "gcp": "cloud", "azure": "cloud",
    "power bi": "visualization", "tableau": "visualization", "matplotlib": "visualization",
    "docker": "mlops", "kubernetes": "mlops", "mlflow": "mlops", "kubeflow": "mlops",
    "sql": "data", "postgresql": "data", "mongodb": "data", "snowflake": "data", "bigquery": "data",
    "python": "coding", "java": "coding", "javascript": "coding", "typescript": "coding"
}

def clean_narrative(text):
    """Removing all numeric mentions and re-calculated metrics from LLM narrative."""
    import re
    # Remove "experience delta" or "match score" sentences entirely
    text = re.sub(r"(?i)(experience delta|match score|verdict).*?([.!?]|$)", "", text)
    # Remove any stray numeric phrases that look like metrics
    text = re.sub(r"\d+%", "", text)
    return text.strip()

def strict_skill_firewall(output, data):
    """Bi-directional skill enforcement: Kill hallucinations & Force evidence."""
    allowed_strengths = set(s.lower().strip() for s in data["extracted_skills"])
    allowed_weaknesses = set(s.lower().strip() for s in data["missing_skills"])

    # 1. Purge hallucinations
    raw_strengths = [s for s in output.get("strengths", []) if str(s).lower().strip() in allowed_strengths]
    
    # 2. Force Include Real Evidence (If LLM is lazy, we restore the truth)
    # We take the top 8 extracted skills as verified strengths
    output["strengths"] = list(allowed_strengths)[:12]

    # 3. Purge weak hallucinations
    output["weaknesses"] = [
        s for s in output.get("weaknesses", [])
        if str(s).lower().strip() in allowed_weaknesses
    ]
    # Ensure all missing skills are represented
    if not output["weaknesses"]:
        output["weaknesses"] = list(allowed_weaknesses)

    return output

def build_interview_ready_roadmap(missing_skills: list) -> list:
    weeks = [[] for _ in range(4)]
    for i, skill in enumerate(missing_skills):
        weeks[i % 4].append(skill)

    roadmap = []
    themes = ["Foundation", "Core Build", "Deployment", "Integration"]
    
    for i, (ws, theme) in enumerate(zip(weeks, themes), 1):
        actual_skills = ws if ws else ["Architectural Optimization"]
        actions = []
        for s in actual_skills:
            skill_low = s.lower().strip()
            t = SKILL_TYPES.get(skill_low, "general")
            if t == "ml": actions.append(f"Build and evaluate optimized machine learning models using {s}. Implement production-grade training loops.")
            elif t == "cloud": actions.append(f"Architect and deploy scalable infrastructure on {s.upper()}. Configure baseline IAM and resource scaling.")
            elif t == "visualization": actions.append(f"Create advanced analytical dashboards using {s} mapped to business KPIs.")
            elif t == "mlops": actions.append(f"Containerize and orchestrate engineering pipelines using {s}. Implement automated deployment hooks.")
            else: actions.append(f"Develop robust, production-grade logic and architectural patterns using {s}.")
            
        roadmap.append({
            "week": i,
            "theme": theme,
            "skills": actual_skills,
            "objective": f"Gain working implementation of {', '.join(actual_skills)}",
            "actions": actions,
            "output": f"Demonstrable implementation of {', '.join(actual_skills)}"
        })
    return roadmap

def build_prompt(payload: dict) -> str:
    return f"""
Persona: Senior Technical Recruiter (ARIA)
Goal: Analyze candidate based on provided EVIDENCE only.

NON-NEGOTIABLE RULES:
1. Use EXACT data provided. 
2. DO NOT calculate experience gap.
3. DO NOT state numeric delta or match score values in your insight.
4. Response MUST be valid JSON.

=== SYSTEM DATA (SSOT) ===
Candidate: {payload['candidate_name']}
Target: {payload['jd_title']}
Verdict: {payload['verdict']}

=== EVIDENCE ===
Strengths (ONLY USE THESE): {', '.join(payload['skills'])}
Weaknesses (ONLY USE THESE): {', '.join(payload['missing_skills'])}

=== OUTPUT SCHEMA ===
{{
  "recruiterInsight": "3-4 sentences of diagnostic professional analysis.",
  "strengths": ["list from provided strengths"],
  "weaknesses": ["list from provided weaknesses"]
}}
"""

def ultimate_firewall(output, data):
    if not isinstance(output, dict): output = {}
    
    # 1. Skill Enforcement
    output = strict_skill_firewall(output, data)
    
    # 2. Narrative Cleaning (Numeric Purge)
    output["recruiterInsight"] = clean_narrative(output.get("recruiterInsight", "Technical analysis baseline established."))
    
    # 3. SSOT Injection
    output["match_score"] = data["match_score"]
    output["experience_delta"] = data["experience_delta"]
    output["hiringVerdict"] = {
        "decision": data["verdict"],
        "justification": f"Deterministic assessment based on {data['match_score']}% technical alignment."
    }
    
    # 4. Roadmap Injection
    output["roadmap"] = build_interview_ready_roadmap(data["missing_skills"])
    
    return output

def safe_parse_json(text):
    if not text: return {}
    clean = text.replace("```json", "").replace("```", "").strip()
    try: return json.loads(clean)
    except: pass
    match = re.search(r'\{.*\}', clean, re.DOTALL)
    if match:
        try: return json.loads(match.group())
        except: pass
    return {}

def build_fallback(payload: dict, reason: str):
    fb = {"recruiterInsight": f"Standardized analysis based on heuristic data mapping.", "strengths": [], "weaknesses": []}
    return ultimate_firewall(fb, payload)
