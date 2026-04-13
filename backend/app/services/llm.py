import json
import logging
import re
from typing import Any, Dict

import httpx
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential
from groq import AsyncGroq

from app.core.config import get_settings
from app.core.errors import NetworkAppError, ProviderAppError
from app.models.schemas import AnalyzeRequest, LLMFeedback, ScoreResponse

logger = logging.getLogger(__name__)


def _feedback_prompt(payload: AnalyzeRequest, score: ScoreResponse) -> str:
    return f"""
You are a senior AI recruiter. Return only valid JSON with keys:
verdict, experience_assessment, full_analysis, improvement_recommendations (array).

Use this computed ML context:
- final_score: {score.final_score}
- probability: {score.probability}
- tfidf_score: {score.tfidf_score}
- embedding_score: {score.embedding_score}
- skill_match: {score.skill_match}
- experience_score: {score.experience_score}
- matched_skills: {score.matched_skills}
- missing_skills: {score.missing_skills}
- years_resume: {score.years_resume}
- years_required: {score.years_required}

RESUME:
{payload.resume}

JOB DESCRIPTION:
{payload.job_description}
""".strip()


def _extract_json(text: str) -> Dict[str, Any]:
    stripped = text.strip().replace("```json", "").replace("```", "")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(2), reraise=True)
async def _call_anthropic(prompt: str) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ProviderAppError("Missing ANTHROPIC_API_KEY.")
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "max_tokens": settings.llm_max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
    if response.status_code >= 500:
        raise NetworkAppError(f"Anthropic network/server issue ({response.status_code}).")
    if response.status_code >= 400:
        raise ProviderAppError(f"Anthropic provider error ({response.status_code}): {response.text[:250]}")
    data = response.json()
    return "".join(
        block.get("text", "") for block in data.get("content", []) if isinstance(block, dict) and block.get("type") == "text"
    )


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(2), reraise=True)
async def _call_openai(prompt: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ProviderAppError("Missing OPENAI_API_KEY.")
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "content-type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            },
        )
    if response.status_code >= 500:
        raise NetworkAppError(f"OpenAI network/server issue ({response.status_code}).")
    if response.status_code >= 400:
        raise ProviderAppError(f"OpenAI provider error ({response.status_code}): {response.text[:250]}")
    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise ProviderAppError("OpenAI returned empty choices.")
    return choices[0]["message"]["content"]


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(2), reraise=True)
async def _call_groq(prompt: str) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise ProviderAppError("Missing GROQ_API_KEY.")
    client = AsyncGroq(api_key=settings.groq_api_key)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=settings.llm_max_tokens,
    )
    return response.choices[0].message.content


async def _repair_with_llm(raw_text: str) -> Dict[str, Any]:
    repair_prompt = f"""
Fix this malformed JSON. Return only a valid JSON object, no prose:
{raw_text}
""".strip()
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "openai":
        repaired = await _call_openai(repair_prompt)
    elif provider == "groq":
        repaired = await _call_groq(repair_prompt)
    else:
        repaired = await _call_anthropic(repair_prompt)
    return _extract_json(repaired)


async def generate_llm_feedback(payload: AnalyzeRequest, score: ScoreResponse) -> LLMFeedback:
    settings = get_settings()
    prompt = _feedback_prompt(payload, score)
    provider = settings.llm_provider.lower()
    try:
        if provider == "openai":
            raw = await _call_openai(prompt)
        elif provider == "groq":
            raw = await _call_groq(prompt)
        else:
            raw = await _call_anthropic(prompt)
    except (ProviderAppError, NetworkAppError):
        raise
    except Exception as exc:
        logger.exception("llm_request_failure")
        raise NetworkAppError(f"LLM request failed: {str(exc)}") from exc

    # Strict response schema validation + auto-repair fallback.
    try:
        parsed = _extract_json(raw)
        return LLMFeedback.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError):
        logger.warning("llm_json_invalid_attempting_repair")
        try:
            repaired = await _repair_with_llm(raw)
            return LLMFeedback.model_validate(repaired)
        except Exception as exc:
            raise ProviderAppError(f"Invalid LLM JSON response after repair attempt: {str(exc)}") from exc
