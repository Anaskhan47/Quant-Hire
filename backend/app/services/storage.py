import hashlib
import json
from typing import Any, Dict, List

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.db import AnalysisRecord, Base

_engine = None
_SessionLocal = None


def init_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        return
    settings = get_settings()
    url = getattr(settings, "database_url", "sqlite:///./resume_ai.db")
    _engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)


def get_session() -> Session:
    if _SessionLocal is None:
        init_engine()
    return _SessionLocal()


def _hash_request(resume: str, jd: str) -> str:
    h = hashlib.sha256()
    h.update(resume.encode("utf-8"))
    h.update(b"||")
    h.update(jd.encode("utf-8"))
    return h.hexdigest()


def persist_analysis(request: Dict[str, Any], response: Dict[str, Any]) -> None:
    resume = request.get("resume", "")
    jd = request.get("job_description", "")
    rec = AnalysisRecord(
        request_hash=_hash_request(resume, jd),
        resume_snippet=resume[:4000],
        jd_snippet=jd[:4000],
        match_score=int(response.get("match_score", 0)),
        shortlist_probability=int(response.get("shortlist_probability", 0)),
        skill_match_pct=int(response.get("skill_match_pct", 0)),
        resume_quality_score=int(response.get("resume_quality_score", 0)),
        payload=json.loads(json.dumps(response)),
    )
    with get_session() as session:
        session.add(rec)
        session.commit()


def get_recent_analyses(limit: int = 20) -> List[Dict[str, Any]]:
    with get_session() as session:
        stmt = select(AnalysisRecord).order_by(AnalysisRecord.id.desc()).limit(limit)
        rows = session.execute(stmt).scalars().all()
        return [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "match_score": r.match_score,
                "shortlist_probability": r.shortlist_probability,
                "skill_match_pct": r.skill_match_pct,
                "resume_quality_score": r.resume_quality_score,
            }
            for r in rows
        ]

