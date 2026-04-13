import logging
import traceback
import sys
import datetime
import math
import re
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import groq
from engine import (
    build_prompt, 
    safe_parse_json, 
    ultimate_firewall, 
    build_fallback
)

# —————————————————————————————————————————————
# SYSTEM CONFIG & LOGGING
# —————————————————————————————————————————————

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except:
    pass

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("recruitiq.v1")

load_dotenv()
try:
    groq_client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
except:
    groq_client = None

# —————————————————————————————————————————————
# SKILL & HEURISTIC ENGINE (ULTRA-DEEP ANALYZER)
# —————————————————————————————————————————————

# Expanded Library for Deep Analysis
SKILL_LIBRARY = [
    "python","java","javascript","typescript","go","rust","c++","c#","ruby","php","swift","kotlin","scala","r",
    "tensorflow","pytorch","keras","scikit-learn","xgboost","lightgbm","huggingface","transformers",
    "nlp","computer vision","llm","rag","mlops","mlflow","kubeflow","feature engineering",
    "sql","postgresql","mysql","mongodb","redis","elasticsearch","apache spark","hadoop","kafka",
    "airflow","dbt","snowflake","bigquery","pandas","numpy","matplotlib","tableau","power bi",
    "aws","gcp","azure","docker","kubernetes","terraform","helm","argocd","ci/cd","github actions",
    "jenkins","ansible","linux","bash","prometheus","grafana",
    "react","next.js","vue","angular","node.js","django","fastapi","flask","graphql","rest api",
    "team leadership","agile","scrum","stakeholder management","communication","problem solving",
    "git","jira","figma","system design","microservices","distributed systems","grpc"
]

def extract_skills(text):
    text_lower = text.lower()
    found = []
    for skill in SKILL_LIBRARY:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill)
    return list(set(found))

def extract_years(text):
    patterns = [r'(\d+)\+?\s*years?\b', r'(\d+)\s*yrs?\b']
    years = [3]  # Default
    for p in patterns:
        matches = re.findall(p, text.lower())
        for m in matches:
            try:
                val = int(m)
                if 1 <= val < 50: years.append(val)
            except: continue
    return max(years)

def extract_jd_required_years(jd_text):
    patterns = [r'(\d+)\+?\s*years?\b', r'minimum\s*(\d+)\s*years?\b']
    for p in patterns:
        m = re.search(p, jd_text.lower())
        if m: return int(m.group(1))
    return 3

def compute_score(resume_skills, jd_skills, resume_years, required_years, skill_match_pct):
    skill_feat = skill_match_pct / 100.0
    exp_feat = min(resume_years / max(required_years, 1), 1.5) / 1.5
    raw = (skill_feat * 0.6) + (exp_feat * 0.4)
    return int(max(10, min(97, raw * 100)))

def compute_features(resume_skills, jd_skills, resume_years, required_years, skill_match_pct):
    return {
        "experienceMatch": int(min(resume_years/max(required_years,1)*100, 100)),
        "skillCoverage": int(skill_match_pct),
        "projectRelevance": int(min(skill_match_pct * 1.1, 100)),
        "seniorityAlignment": int(min(resume_years/max(required_years,1)*100, 100)),
        "domainFit": int(skill_match_pct)
    }

# —————————————————————————————————————————————
# ARIA ULTIMATE PIPELINE
# —————————————————————————————————————————————

def generate_llm_insight(payload, max_retries=2):
    if not groq_client: return {}
    prompt = build_prompt(payload)
    for attempt in range(max_retries):
        try:
            model_id = "llama-3.3-70b-versatile" if attempt == 0 else "llama-3.1-8b-instant"
            response = groq_client.chat.completions.create(
                model=model_id, 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800
            )
            raw = response.choices[0].message.content or ""
            parsed = safe_parse_json(raw)
            if parsed and parsed.get("recruiterInsight"): return parsed
        except Exception: continue
    return {}

def format_ui_response(llm_data, core_data, display_data):
    # This combines all 3 layers for the final JSON return
    insight = llm_data.get("recruiterInsight", "Technical analysis baseline established.")
    strengths_md = "\n".join([f"* {s}" for s in llm_data.get("strengths", [])])
    weaknesses_md = "\n".join([f"* {w}" for w in llm_data.get("weaknesses", [])])
    verdict_info = llm_data.get("hiringVerdict", {})
    
    analysis_md = (
        f"### AI Recruiter Insight\n{insight}\n\n"
        f"### Strengths\n{strengths_md if strengths_md else '* No strong evidence matches.'}\n\n"
        f"### Weaknesses\n{weaknesses_md if weaknesses_md else '* No critical gaps identified.'}\n\n"
        f"### Hiring Verdict\n**{verdict_info.get('decision', 'Review')}** — {verdict_info.get('justification', '')}"
    )
    
    roadmap_parts = []
    for w in llm_data.get("roadmap", []):
        roadmap_parts.append(
            f"#### Week {w['week']}: {w['theme']}\n"
            f"**Objective:** {w['objective']}\n"
            f"**Skills:** {', '.join(w['skills'])}\n"
            f"**Actions:**\n" + "\n".join([f"→ {a}" for a in w['actions']]) +
            f"\n**Demo Output:** {w['output']}"
        )
    return analysis_md, "\n\n".join(roadmap_parts)

# —————————————————————————————————————————————
# REST API (FIREWALL ENFORCED)
# —————————————————————————————————————————————

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json(force=True)
        r_text = data.get('resume_text', '').strip()
        jd_text = data.get('job_description', '').strip()
        
        if not r_text or not jd_text: return jsonify({'error': 'Missing input'}), 400
        
        # 🟢 1. CORE DATA (SSOT)
        r_skills, jd_skills = extract_skills(r_text), extract_skills(jd_text)
        matched = [s for s in jd_skills if s in r_skills]
        missing = [s for s in jd_skills if s not in r_skills]
        skill_pct = round(len(matched) / max(len(jd_skills), 1) * 100)
        r_yrs, r_req = extract_years(r_text), extract_jd_required_years(jd_text)
        score = compute_score(r_skills, jd_skills, r_yrs, r_req, skill_pct)
        
        CORE_DATA = {
            "candidate_name": r_text.split('\n')[0][:50].split('—')[0].strip(),
            "jd_title": jd_text.split('\n')[0][:50],
            "match_score": float(score),
            "experience_delta": float(r_yrs - r_req),
            "verdict": "Reject" if score < 50 else ("Consider" if score < 75 else "Strong Hire"),
            "extracted_skills": r_skills,
            "missing_skills": missing
        }

        # 🔵 2. DISPLAY DATA (UI ONLY - NEVER SEEN BY LLM)
        features = compute_features(r_skills, jd_skills, r_yrs, r_req, skill_pct)
        DISPLAY_DATA = {
            "technical_coverage": skill_pct,
            "feature_trace": features,
            "matched_list": matched
        }

        # 🟡 3. LLM PAYLOAD (STRICT CLEAN)
        llm_payload = {
            "candidate_name": CORE_DATA["candidate_name"],
            "jd_title": CORE_DATA["jd_title"],
            "match_score": CORE_DATA["match_score"],
            "experience_delta": CORE_DATA["experience_delta"],
            "verdict": CORE_DATA["verdict"],
            "skills": CORE_DATA["extracted_skills"],
            "missing_skills": CORE_DATA["missing_skills"]
        }
        
        # 🚀 4. FIREWALL PIPELINE
        raw_llm = generate_llm_insight(llm_payload)
        final_llm = ultimate_firewall(raw_llm, CORE_DATA)
        
        ai_md, roadmap_md = format_ui_response(final_llm, CORE_DATA, DISPLAY_DATA)
        
        return jsonify({
            "candidateName": CORE_DATA["candidate_name"],
            "verdict": final_llm["hiringVerdict"]["justification"],
            "analysis": {
                "overall_match": CORE_DATA["match_score"], 
                "shortlist_probability": CORE_DATA["match_score"], 
                "skill_density": DISPLAY_DATA["technical_coverage"], 
                "structural_fit": DISPLAY_DATA["feature_trace"]["domainFit"]
            },
            "skills": {"matched": matched, "missing": missing},
            "feature_trace": {
                "keyword_alignment": DISPLAY_DATA["technical_coverage"], 
                "semantic_match": DISPLAY_DATA["feature_trace"]["projectRelevance"], 
                "experience_fit": DISPLAY_DATA["feature_trace"]["experienceMatch"], 
                "seniority_alignment": DISPLAY_DATA["feature_trace"]["seniorityAlignment"]
            },
            "ai_analysis": ai_md, 
            "roadmap": roadmap_md, 
            "insights": [] 
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f"Ultimate Firewall Violation: {str(e)}"}), 500

@app.route('/health')
def health(): return jsonify({'status': 'ok', 'engine': 'ARIA-Ultimate'}), 200

if __name__ == '__main__':
    log.info("🚀 RecruitIQ ARIA Ultimate booting on port 8003...")
    app.run(host='0.0.0.0', port=8003, debug=False)
