from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AnalysisRecord(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    request_hash = Column(String(64), index=True, nullable=False)
    resume_snippet = Column(Text, nullable=False)
    jd_snippet = Column(Text, nullable=False)
    match_score = Column(Integer, nullable=False)
    shortlist_probability = Column(Integer, nullable=False)
    skill_match_pct = Column(Integer, nullable=False)
    resume_quality_score = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)

