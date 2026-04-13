import logging
import time
import traceback
import json
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.metrics import metrics
from .models.loader import model_loader
from .schemas.predict import PredictRequest, PredictResponse
from .services.scoring import scoring_pipeline
from fastapi.staticfiles import StaticFiles
from .utils.extractor import text_extractor

# Structured JSON Logger (Production Level)
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("backend.production")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(json.dumps({"event": "SYSTEM_BOOTSTRAP", "msg": "Starting Career Intelligence Engine..."}))
    try:
        _ = model_loader
        status = "ok" if model_loader.ml_model and model_loader.emb_model else "degraded"
        log.info(json.dumps({"event": "SYSTEM_READY", "status": status}))
    except Exception as e:
        log.critical(json.dumps({"event": "BOOTSTRAP_FAILURE", "error": str(e)}))
    yield

app = FastAPI(title="RecruitIQ Production Engine", version="4.6.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.APP_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount asset directories from root
app.mount("/css", StaticFiles(directory="../css"), name="css")
app.mount("/js", StaticFiles(directory="../js"), name="js")
app.mount("/pipeline", StaticFiles(directory="../pipeline"), name="pipeline")

@app.post("/predict", response_model=PredictResponse)
@app.post("/v2/predict", response_model=PredictResponse)
async def predict_v2(request: PredictRequest):
    """Refined V2: Hardened Prediction Engine with Cache-Busting Interface."""
    start_time = time.perf_counter()
    rid = f"REQ-V2-{uuid.uuid4().hex[:6].upper()}"
    
    log.info(json.dumps({"event": "PREDICT_V2_START", "rid": rid}))
    
    try:
        # 1. 🔍 Explicit Field Presence check (Direct mapping for V2 stability)
        r_txt = getattr(request, 'resume', '').strip()
        jd_txt = getattr(request, 'job_description', '').strip()
        
        if not r_txt or not jd_txt:
            log.warning(json.dumps({"event": "VALIDATION_REJECTION", "rid": rid, "reason": "EMPTY_FIELD"}))
            raise HTTPException(status_code=422, detail="V2_ERROR: Input fields cannot be empty.")

        # 2. ⚡ Execute Pipeline
        log.info(json.dumps({"event": "V2_PIPELINE_INITIATED", "rid": rid}))
        result = await scoring_pipeline.process_analysis(r_txt, jd_txt)
        
        latency = round(time.perf_counter() - start_time, 3)
        log.info(json.dumps({"event": "V2_PREDICT_SUCCESS", "rid": rid, "latency_sec": latency}))
        return result

    except HTTPException: raise
    except Exception as e:
        print(f"🔥 V2 PIPELINE CRASH detected: {str(e)}")
        traceback.print_exc()
        
        raise HTTPException(status_code=500, detail=f"V2_ENGINE_FAULT: {str(e)} (ID: {rid})")

@app.post("/predict-pdf", response_model=PredictResponse)
async def predict_pdf(
    resume_file: UploadFile = File(...),
    job_description: str = Form(...)
):
    """Hardened Document entry point with boundary checks."""
    fname = resume_file.filename.lower()
    
    try:
        content = await resume_file.read()
        if fname.endswith(".pdf"):
            resume_text = await text_extractor.extract_from_pdf(content)
        elif fname.endswith(".txt"):
            resume_text = content.decode("utf-8", errors="ignore")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Provide PDF or TXT.")
        
        if not resume_text or len(resume_text.strip()) < 50:
             raise HTTPException(status_code=422, detail="Document content too brief for AI analysis.")
             
        return await scoring_pipeline.process_analysis(resume_text, job_description)
    except HTTPException: raise
    except Exception as e:
        log.error(json.dumps({"event": "DOCUMENT_REJECTION", "error": str(e)}))
        raise HTTPException(status_code=500, detail="Failed to process document content.")

@app.post("/extract")
async def extract_text_from_file(file: UploadFile = File(...)):
    """Generic text extraction from PDF or TXT."""
    try:
        content = await file.read()
        if file.filename.lower().endswith(".pdf"):
            text = await text_extractor.extract_from_pdf(content)
        else:
            text = content.decode("utf-8", errors="ignore")
        return {"text": text}
    except Exception as e:
        log.error(f"Extraction failed for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract text from file.")

@app.get("/health")
def health():
    """Detailed System Health (Rule 6)."""
    is_ml_loaded = model_loader.ml_model is not None
    is_emb_loaded = model_loader.emb_model is not None
    
    return {
        "model_loaded": is_ml_loaded,
        "embedding_ready": is_emb_loaded,
        "llm_ready": True, # Managed by AsyncGroq
        "system_status": "ok" if is_ml_loaded and is_emb_loaded else "degraded",
        "engine_v": "4.6.1-prod"
    }

@app.get("/")
async def root():
    """Serve the root QuantHire UI (Rule 1)."""
    return FileResponse("../index.html")

@app.get("/metrics")
def get_metrics():
    """Deployment Observability Metrics (Rule 8)."""
    return metrics.get_stats()
