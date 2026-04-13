# Resume AI Analyzer - Production Backend + Frontend

This project is now split into:

- `frontend` (existing static files in root): `index.html`, `css/style.css`, `js/app.js`
- `backend` (new): FastAPI service with real ML scoring, secure LLM integration, validation, tests, and observability primitives.

## 1) Folder structure

```text
resume_ai_analyzer/
  index.html
  css/style.css
  js/app.js
  backend/
    app/
      main.py
      core/
        config.py
        errors.py
        logging.py
      middleware/
        request_context.py
      models/
        schemas.py
      routes/
        analyze.py
      services/
        text_utils.py
        scoring.py
        llm.py
        pipeline.py
    tests/
      test_scoring.py
      test_api.py
    requirements.txt
    .env.example
```

## 2) Why this architecture

- **FastAPI**: typed contracts, performance, validation, and easy testability.
- **Separation of concerns**:
  - Routes handle transport (`/api/*`).
  - Services handle logic (ML scoring, LLM calls, orchestration).
  - Models enforce strict request/response schemas.
  - Core layer handles config, logging, and error categories.
- **Security**: API keys only on backend via environment variables.
- **Scalability**: scoring + LLM services are isolated so you can replace or scale independently.

## 3) Backend implementation details

### Config and secrets

- Environment variables are managed by `pydantic-settings` in `backend/app/core/config.py`.
- Copy and edit:

```bash
cd backend
cp .env.example .env
```

Set at minimum:

- `LLM_PROVIDER=anthropic` or `openai`
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- `LLM_MODEL`

### ML scoring engine (`backend/app/services/scoring.py`)

Implements real computation:

- TF-IDF similarity (`scikit-learn`)
- Sentence embedding cosine similarity (`sentence-transformers`)
- Skill extraction + overlap scoring
- Experience gap scoring
- Weighted final score and logistic shortlist probability

Response shape:

```json
{
  "tfidf_score": 0,
  "embedding_score": 0,
  "skill_match": 0,
  "experience_score": 0,
  "final_score": 0,
  "probability": 0
}
```

### LLM integration (`backend/app/services/llm.py`)

- Provider abstraction for Anthropic/OpenAI.
- Retry logic with exponential backoff (`tenacity`).
- Strict schema validation using Pydantic (`LLMFeedback`).
- Auto-repair fallback for malformed JSON responses.
- Error categories:
  - `validation` (422)
  - `provider` (502)
  - `network` (503)

### API routes (`backend/app/routes/analyze.py`)

- `POST /api/score` -> ML scoring only
- `POST /api/llm-feedback` -> recommendation-only path
- `POST /api/analyze` -> full pipeline (score + LLM)
- `GET /api/health` -> health check

### Validation and guardrails

`AnalyzeRequest` in `backend/app/models/schemas.py` enforces:

- Empty input protection
- Min/max input lengths
- Basic sanitization and normalization

## 4) Frontend integration

`js/app.js` now calls:

- `POST http://127.0.0.1:8000/api/analyze`

instead of calling Anthropic directly.

## 5) Local run

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

Serve project root with any static server (or VS Code Live Server), then open `index.html`.

## 6) Testing

From `backend`:

```bash
pytest -q
```

Included tests:

- Unit tests for scoring behavior and ranges
- Integration tests for API endpoints
- Mocked LLM test for `/api/analyze`

## 7) Deployment

### Backend on Render/Railway

1. Create service from repo root, set working dir to `backend`.
2. Build/install:
   - `pip install -r requirements.txt`
3. Start:
   - `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Configure environment variables from `.env.example`.
5. Restrict `APP_ALLOWED_ORIGINS` to your frontend domain.

### Frontend on Vercel

1. Import repo.
2. Set root as project root.
3. Deploy static files.
4. Update frontend API URL in `js/app.js` to your backend URL (or introduce runtime config).

## 8) Observability

Implemented:

- JSON structured logging in `core/logging.py`
- Request ID middleware in `middleware/request_context.py`
- Request ID returned in `X-Request-ID`

Recommended next:

- Add Sentry SDK for exception tracking.
- Export logs to Datadog/ELK/Loki.
- Add latency metrics with Prometheus instrumentation.

## 9) Final pipeline example

`POST /api/analyze`

Request:

```json
{
  "resume": "Senior Python Engineer with 6 years in FastAPI, AWS, Docker, NLP...",
  "job_description": "Looking for ML Engineer with Python, FastAPI, Docker, AWS, NLP, 4+ years..."
}
```

Response:

- `match_score`
- `shortlist_probability`
- `skill_match_pct`
- `resume_quality_score`
- `matched_skills` / `missing_skills`
- `features` map (tfidf, embeddings, experience, consistency)
- `verdict`, `experience_assessment`, `full_analysis`

This is now a production-grade foundation you can scale with:
- async queue for expensive embedding/LLM steps
- persisted analysis history (PostgreSQL)
- model calibration with historical hiring outcomes
