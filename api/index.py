import sys
import os
from pathlib import Path

# ── Path Bootstrap ────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MODEL_DIR", str(ROOT / "pipeline" / "artifacts"))

# ── Imports ───────────────────────────────────────────────────────────────────
import uuid
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from backend.app.schemas.predict import PredictRequest, PredictResponse
from backend.app.services.scoring import scoring_pipeline
from backend.app.models.loader import model_loader
from backend.app.utils.extractor import text_extractor

# ── FastAPI App ───────────────────────────────────────────────────────────────
# We use root_path="/api" so that the routes match the /api/* requests from Vercel
app = FastAPI(title="QuantHire API", version="4.6.1", root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/predict", response_model=PredictResponse)
@app.post("/v2/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Main AI scoring endpoint."""
    rid = f"REQ-{uuid.uuid4().hex[:6].upper()}"
    r_txt = (request.resume or "").strip()
    jd_txt = (request.job_description or "").strip()

    if not r_txt or not jd_txt:
        raise HTTPException(status_code=422, detail="Both resume and job_description are required.")

    try:
        result = await scoring_pipeline.process_analysis(r_txt, jd_txt)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline error (ID: {rid}): {str(e)}")

@app.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    """Extract plain text from an uploaded PDF or TXT file."""
    try:
        content = await file.read()
        if file.filename.lower().endswith(".pdf"):
            text = await text_extractor.extract_from_pdf(content)
        else:
            text = content.decode("utf-8", errors="ignore")
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.get("/health")
def health():
    """Liveness + readiness check."""
    ml_ok = model_loader.ml_model is not None
    return {
        "model_loaded": ml_ok,
        "embedding_ready": model_loader.emb_model is not None,
        "system_status": "ok" if ml_ok else "degraded",
        "engine_v": "4.6.1-prod",
    }

# Vercel handler
handler = Mangum(app)
