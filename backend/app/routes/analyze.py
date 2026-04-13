from fastapi import APIRouter, File, Form, UploadFile

from app.models.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse, LLMFeedback, ScoreResponse
from app.services.llm import generate_llm_feedback
from app.services.pipeline import run_full_analysis
from app.services.scoring import compute_ml_scores
from app.services.storage import get_recent_analyses
from app.services.pdf import extract_text_from_pdf_bytes
from app.core.config import get_settings
from app.core.errors import ValidationAppError

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="resume-ai-analyzer")


@router.get("/analyses/recent")
async def recent_analyses():
    return {"items": get_recent_analyses()}


@router.post("/score", response_model=ScoreResponse)
async def score(payload: AnalyzeRequest) -> ScoreResponse:
    return compute_ml_scores(payload)


@router.post("/llm-feedback", response_model=LLMFeedback)
async def llm_feedback(payload: AnalyzeRequest) -> LLMFeedback:
    score_result = compute_ml_scores(payload)
    return await generate_llm_feedback(payload, score_result)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    return await run_full_analysis(payload)


@router.post("/analyze-pdf", response_model=AnalyzeResponse)
async def analyze_pdf(
    resume_file: UploadFile = File(...),
    job_description: str = Form(...),
) -> AnalyzeResponse:
    settings = get_settings()

    filename = (resume_file.filename or "").lower()
    ext = filename.split(".")[-1] if "." in filename else ""
    allowed = {e.strip().lower() for e in settings.allowed_resume_file_extensions.split(",") if e.strip()}
    if ext not in allowed:
        raise ValidationAppError(f"Unsupported resume file type: .{ext}. Allowed: {sorted(allowed)}")

    pdf_bytes = await resume_file.read()
    if len(pdf_bytes) > settings.max_resume_file_bytes:
        raise ValidationAppError("Resume file too large. Please upload a smaller PDF.")

    resume_text = extract_text_from_pdf_bytes(pdf_bytes)
    if not resume_text:
        raise ValidationAppError("Could not extract text from the uploaded PDF. Please upload a text-based PDF or paste the resume text.")

    payload = AnalyzeRequest(resume=resume_text, job_description=job_description)
    return await run_full_analysis(payload)
