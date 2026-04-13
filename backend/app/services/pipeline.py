from app.core.errors import NetworkAppError, ProviderAppError
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.llm import generate_llm_feedback
from app.services.scoring import compute_ml_scores, feature_map
from app.services.storage import persist_analysis


def _fallback_feedback(payload: AnalyzeRequest, score) -> tuple[str, str, str]:
    missing = ", ".join(score.missing_skills[:8]) if score.missing_skills else "no major missing skills"
    verdict = (
        "Strong recruiter fit"
        if score.final_score >= 75
        else "Moderate fit with upskilling needed"
        if score.final_score >= 55
        else "Low fit for current role"
    )
    experience_assessment = (
        f"Detected {score.years_resume} years in resume vs {score.years_required} years required. "
        "Experience alignment is estimated from explicit year mentions and role history."
    )
    full_analysis = (
        "**MATCH SUMMARY**\n"
        f"Automated ML scoring indicates an overall match score of {round(score.final_score)}% with shortlist probability {round(score.probability)}%.\n\n"
        "**MISSING SKILLS & GAPS**\n"
        f"The main identified gaps are: {missing}.\n\n"
        "**RESUME STRENGTHS**\n"
        f"Matched skills: {', '.join(score.matched_skills[:10]) if score.matched_skills else 'limited explicit skill overlap'}.\n\n"
        "**WEAK AREAS**\n"
        "Some requirements may be implicit in resume wording and not explicitly stated.\n\n"
        "**IMPROVEMENT RECOMMENDATIONS**\n"
        "Add measurable impact bullets, explicitly mention missing tools, and tailor summary to the target JD."
    )
    return verdict, experience_assessment, full_analysis


async def run_full_analysis(payload: AnalyzeRequest) -> AnalyzeResponse:
    score = compute_ml_scores(payload)
    try:
        feedback = await generate_llm_feedback(payload, score)
        verdict = feedback.verdict
        experience_assessment = feedback.experience_assessment
        full_analysis = feedback.full_analysis
    except (ProviderAppError, NetworkAppError):
        verdict, experience_assessment, full_analysis = _fallback_feedback(payload, score)

    features = feature_map(score)

    response = AnalyzeResponse(
        match_score=round(score.final_score),
        shortlist_probability=round(score.probability),
        skill_match_pct=round(score.skill_match),
        resume_quality_score=round((0.45 * score.embedding_score) + (0.30 * score.tfidf_score) + (0.25 * score.experience_score)),
        experience_years_resume=score.years_resume,
        experience_years_required=score.years_required,
        matched_skills=score.matched_skills,
        missing_skills=score.missing_skills,
        features=features,
        verdict=verdict,
        experience_assessment=experience_assessment,
        full_analysis=full_analysis,
    )
    persist_analysis(payload.model_dump(), response.model_dump())
    return response
