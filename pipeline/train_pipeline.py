"""
RecruitIQ — End-to-End ML Training Pipeline
=============================================
Production-grade pipeline for training resume-to-job-description matching models.

Datasets:
  - Resume.csv       → 2484 resumes with Category labels
  - training_data.csv → 853 job descriptions with position titles

Pipeline:
  1. Load & combine data
  2. Create resume-JD pairs with synthetic match labels
  3. Preprocess text
  4. Feature engineering (TF-IDF, embeddings, skill overlap, length diff)
  5. Train models (LogisticRegression, RandomForest)
  6. Evaluate & output results
  7. Export trained artifacts

Author: RecruitIQ ML Pipeline
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("pipeline")


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "Data"
OUTPUT_DIR = Path(__file__).resolve().parent / "artifacts"
MAX_TEXT_LEN = 3000
TFIDF_MAX_FEATURES = 5000
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TEST_SIZE = 0.20
RANDOM_STATE = 42
SAMPLE_PAIRS = 800  # reduced for speed

# Category → plausible job-title keyword mapping for synthetic labelling
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "information-technology": ["software", "developer", "engineer", "programmer", "it ", "data", "devops", "cloud", "systems", "web developer", "full stack"],
    "business-development": ["business", "development", "strategy", "partnerships", "growth", "account"],
    "engineering": ["engineer", "mechanical", "civil", "electrical", "design engineer", "manufacturing"],
    "finance": ["finance", "financial", "analyst", "accounting", "investment", "banking", "bank"],
    "accountant": ["accountant", "accounting", "bookkeep", "auditor", "tax", "cpa"],
    "sales": ["sales", "retail", "account executive", "business development rep"],
    "hr": ["hr", "human resources", "recruiter", "talent", "people operations"],
    "advocate": ["lawyer", "legal", "attorney", "advocate", "paralegal", "counsel"],
    "healthcare": ["nurse", "medical", "health", "clinical", "patient", "physician"],
    "teacher": ["teacher", "instructor", "professor", "education", "tutor", "academic"],
    "chef": ["chef", "cook", "culinary", "food", "kitchen", "restaurant", "bakery"],
    "fitness": ["fitness", "trainer", "gym", "coach", "wellness", "exercise"],
    "aviation": ["aviation", "pilot", "flight", "aircraft", "airline", "aerospace"],
    "designer": ["designer", "graphic", "ui", "ux", "creative", "visual", "art director"],
    "digital-media": ["digital", "media", "content", "social media", "marketing", "seo"],
    "agriculture": ["agriculture", "farm", "agri", "crop", "horticulture"],
    "automobile": ["automobile", "automotive", "mechanic", "vehicle", "car"],
    "bpo": ["bpo", "call center", "customer service", "support", "helpdesk"],
    "construction": ["construction", "building", "contractor", "site", "civil"],
    "consultant": ["consultant", "consulting", "advisory", "management consultant"],
    "arts": ["artist", "art", "creative", "museum", "gallery", "performer"],
    "apparel": ["apparel", "fashion", "textile", "clothing", "garment", "merchandise"],
    "banking": ["banking", "bank", "loan", "credit", "teller", "mortgage"],
    "public-relations": ["public relations", "pr ", "communications", "media relations"],
}


# ====================================================================
# STEP 1: DATA LOADING
# ====================================================================
def load_data(data_dir: Path) -> Dict[str, Any]:
    """Load all CSV and JSON files from data_dir into a dict of DataFrames."""
    import pandas as pd

    log.info("=" * 60)
    log.info("STEP 1: DATA LOADING")
    log.info("=" * 60)
    log.info("Scanning directory: %s", data_dir)

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    datasets: Dict[str, pd.DataFrame] = {}

    for f in sorted(data_dir.iterdir()):
        if f.suffix.lower() == ".csv":
            try:
                df = pd.read_csv(f, encoding="utf-8", on_bad_lines="skip")
                datasets[f.name] = df
                log.info("  ✓ Loaded %-30s → %s rows × %s cols", f.name, df.shape[0], df.shape[1])
            except Exception as exc:
                log.warning("  ✗ Failed to load %s: %s", f.name, exc)
        elif f.suffix.lower() == ".json":
            try:
                df = pd.read_json(f, encoding="utf-8")
                datasets[f.name] = df
                log.info("  ✓ Loaded %-30s → %s rows × %s cols", f.name, df.shape[0], df.shape[1])
            except Exception as exc:
                log.warning("  ✗ Failed to load %s: %s", f.name, exc)

    if not datasets:
        raise RuntimeError("No CSV or JSON datasets found in data directory.")

    for name, df in datasets.items():
        log.info("  Columns [%s]: %s", name, list(df.columns))

    return datasets


# ====================================================================
# STEP 2: COLUMN DETECTION & PAIR CREATION
# ====================================================================
def _detect_column(df, candidates: List[str]) -> Optional[str]:
    """Find first matching column name (case-insensitive)."""
    col_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in col_lower:
            return col_lower[cand.lower()]
    return None


def _category_matches_title(category: str, title: str) -> bool:
    """Check if a resume category plausibly matches a job title."""
    cat_lower = category.lower().strip()
    title_lower = title.lower().strip()

    keywords = CATEGORY_KEYWORDS.get(cat_lower, [cat_lower.replace("-", " ")])
    return any(kw in title_lower for kw in keywords)


def create_pairs(datasets: Dict[str, Any], n_pairs: int = SAMPLE_PAIRS):
    """
    Create resume–JD pairs with synthetic labels.

    Strategy:
      - For each resume, find JDs whose position_title matches the resume's Category → label=1
      - Randomly pair with non-matching JDs → label=0
      - Balance positive/negative samples
    """
    import pandas as pd

    log.info("")
    log.info("=" * 60)
    log.info("STEP 2: COLUMN DETECTION & PAIR CREATION")
    log.info("=" * 60)

    # --- Detect resume dataset ---
    resume_df = None
    resume_col = None
    category_col = None
    for name, df in datasets.items():
        col = _detect_column(df, ["Resume_str", "resume_text", "resume", "cv_text", "cv"])
        if col:
            resume_df = df
            resume_col = col
            category_col = _detect_column(df, ["Category", "category", "label", "job_category"])
            log.info("  Resume dataset  : %s → column '%s' (%s rows)", name, resume_col, len(df))
            if category_col:
                log.info("  Category column : '%s'", category_col)
            break

    if resume_df is None or resume_col is None:
        raise RuntimeError("Could not find a resume text column in any dataset.")

    # --- Detect JD dataset ---
    jd_df = None
    jd_col = None
    title_col = None
    for name, df in datasets.items():
        col = _detect_column(df, ["job_description", "jd", "jd_text", "description"])
        if col:
            jd_df = df
            jd_col = col
            title_col = _detect_column(df, ["position_title", "job_title", "title", "role"])
            log.info("  JD dataset      : %s → column '%s' (%s rows)", name, jd_col, len(df))
            if title_col:
                log.info("  Title column    : '%s'", title_col)
            break

    if jd_df is None or jd_col is None:
        raise RuntimeError("Could not find a job description text column in any dataset.")

    # --- Drop rows with missing text ---
    resumes = resume_df[[resume_col] + ([category_col] if category_col else [])].dropna(subset=[resume_col]).copy()
    resumes = resumes.rename(columns={resume_col: "resume"})
    if category_col:
        resumes = resumes.rename(columns={category_col: "category"})

    jds = jd_df[[jd_col] + ([title_col] if title_col else [])].dropna(subset=[jd_col]).copy()
    jds = jds.rename(columns={jd_col: "job_description"})
    if title_col:
        jds = jds.rename(columns={title_col: "position_title"})

    log.info("  Clean resumes: %d | Clean JDs: %d", len(resumes), len(jds))

    # --- Build pairs ---
    rng = np.random.RandomState(RANDOM_STATE)
    pairs: List[Dict[str, Any]] = []
    half = n_pairs // 2

    resumes_arr = resumes.to_dict("records")
    jds_arr = jds.to_dict("records")

    # Positive pairs: matching category ↔ title
    pos_count = 0
    attempts = 0
    max_attempts = half * 20
    while pos_count < half and attempts < max_attempts:
        r = resumes_arr[rng.randint(len(resumes_arr))]
        j = jds_arr[rng.randint(len(jds_arr))]
        cat = r.get("category", "")
        title = j.get("position_title", "")
        if _category_matches_title(cat, title):
            pairs.append({
                "resume": r["resume"],
                "job_description": j["job_description"],
                "category": cat,
                "position_title": title,
                "label": 1,
            })
            pos_count += 1
        attempts += 1

    log.info("  Positive pairs generated: %d (attempts: %d)", pos_count, attempts)

    # If we couldn't get enough positives, fill with random pairs labelled by similarity heuristic
    if pos_count < half:
        log.warning("  Not enough category-title matches. Filling with random positives.")
        while pos_count < half:
            r = resumes_arr[rng.randint(len(resumes_arr))]
            j = jds_arr[rng.randint(len(jds_arr))]
            pairs.append({
                "resume": r["resume"],
                "job_description": j["job_description"],
                "category": r.get("category", ""),
                "position_title": j.get("position_title", ""),
                "label": 1,
            })
            pos_count += 1

    # Negative pairs: non-matching
    neg_count = 0
    while neg_count < half:
        r = resumes_arr[rng.randint(len(resumes_arr))]
        j = jds_arr[rng.randint(len(jds_arr))]
        cat = r.get("category", "")
        title = j.get("position_title", "")
        if not _category_matches_title(cat, title):
            pairs.append({
                "resume": r["resume"],
                "job_description": j["job_description"],
                "category": cat,
                "position_title": title,
                "label": 0,
            })
            neg_count += 1

    rng.shuffle(pairs)
    df_pairs = pd.DataFrame(pairs)
    log.info("  Total pairs: %d (pos=%d, neg=%d)", len(df_pairs), (df_pairs["label"] == 1).sum(), (df_pairs["label"] == 0).sum())

    return df_pairs


# ====================================================================
# STEP 3: DATA PREPROCESSING
# ====================================================================
def preprocess(df):
    """Clean and normalise resume + JD text columns."""
    import pandas as pd

    log.info("")
    log.info("=" * 60)
    log.info("STEP 3: DATA PREPROCESSING")
    log.info("=" * 60)

    initial = len(df)

    # Drop nulls in text columns
    df = df.dropna(subset=["resume", "job_description"]).copy()
    log.info("  Dropped %d null rows → %d remaining", initial - len(df), len(df))

    def clean_text(text: str) -> str:
        if not isinstance(text, str):
            return ""
        # Fix encoding artifacts
        text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        # Strip HTML tags (Resume_html leakage)
        text = re.sub(r"<[^>]+>", " ", text)
        # Lowercase
        text = text.lower()
        # Remove URLs
        text = re.sub(r"https?://\S+|www\.\S+", " ", text)
        # Remove emails
        text = re.sub(r"\S+@\S+\.\S+", " ", text)
        # Remove special chars (keep letters, numbers, basic punctuation)
        text = re.sub(r"[^a-z0-9\s.,;:!?'\-/+#]", " ", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # Truncate
        return text[:MAX_TEXT_LEN]

    df["resume"] = df["resume"].apply(clean_text)
    df["job_description"] = df["job_description"].apply(clean_text)

    # Drop empty after cleaning
    df = df[(df["resume"].str.len() > 20) & (df["job_description"].str.len() > 20)].copy()
    log.info("  After cleaning: %d rows", len(df))
    log.info("  Avg resume length : %d chars", int(df["resume"].str.len().mean()))
    log.info("  Avg JD length     : %d chars", int(df["job_description"].str.len().mean()))

    return df.reset_index(drop=True)


# ====================================================================
# ADVANCED FEATURE HELPERS
# ====================================================================
def extract_section(text: str, section_name: str) -> str:
    """Extract sections like skills, experience, projects using regex."""
    if not isinstance(text, str):
        return ""
    # Find section and grab text until next likely section header
    pattern = rf"(?:{section_name}[^a-z]{{1,5}})(.*?)(?:experience|skills|projects|education|summary|objective|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def extract_experience(text: str) -> int:
    """Extract years of experience using regex."""
    if not isinstance(text, str):
        return 0
    patterns = [r"(\d+)\+?\s*years?", r"(\d+)\+?\s*yrs?"]
    nums = []
    for pattern in patterns:
        nums.extend(int(m) for m in re.findall(pattern, text))
    return max(nums) if nums else 0

def weighted_skill_overlap(resume_text: str, jd_text: str) -> float:
    """Compute weighted overlap score for important skills."""
    WEIGHTS = {
        "python": 1.5, "machine learning": 2.0, "ml": 2.0, "deep learning": 2.0,
        "sql": 1.2, "aws": 1.2, "docker": 1.2, "kubernetes": 1.5, "api": 1.2,
        "nlp": 1.8, "llm": 2.0,
    }
    r_skills = {s: w for s, w in WEIGHTS.items() if re.search(rf"\b{re.escape(s)}\b", resume_text)}
    j_skills = {s: w for s, w in WEIGHTS.items() if re.search(rf"\b{re.escape(s)}\b", jd_text)}
    
    if not j_skills:
        return 0.5
    
    intersection_weight = sum(w for s, w in r_skills.items() if s in j_skills)
    total_jd_weight = sum(j_skills.values())
    return intersection_weight / total_jd_weight if total_jd_weight > 0 else 0.5

def keyword_strength(text: str) -> float:
    """Detect strong keywords and normalize score."""
    if not isinstance(text, str):
        return 0.0
    STRONG_KEYWORDS = ["deployed", "production", "scalable", "api", "real-time", "led", "architected", "optimized"]
    count = sum(1 for kw in STRONG_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", text))
    return min(1.0, count / len(STRONG_KEYWORDS))

# ====================================================================
# STEP 4 + 5 + 6: FEATURE ENGINEERING
# ====================================================================
def feature_engineering(df):
    """
    Compute all features:
      - tfidf_similarity (cosine on TF-IDF vectors)
      - embedding_similarity (sentence-transformers MiniLM)
      - skill_overlap (keyword matching ratio)
      - length_diff (normalised absolute difference)
    """
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    log.info("")
    log.info("=" * 60)
    log.info("STEP 4-6: FEATURE ENGINEERING")
    log.info("=" * 60)

    n = len(df)

    # ------------------------------------------------------------------
    # A. TF-IDF SIMILARITY
    # ------------------------------------------------------------------
    log.info("  [1/4] Computing TF-IDF similarity...")
    t0 = time.time()

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=TFIDF_MAX_FEATURES,
        sublinear_tf=True,
    )

    all_texts = pd.concat([df["resume"], df["job_description"]], ignore_index=True)
    vectorizer.fit(all_texts)

    resume_tfidf = vectorizer.transform(df["resume"])
    jd_tfidf = vectorizer.transform(df["job_description"])

    tfidf_sims = np.array([
        cosine_similarity(resume_tfidf[i:i+1], jd_tfidf[i:i+1])[0][0]
        for i in range(n)
    ])
    df["tfidf_similarity"] = np.clip(tfidf_sims, 0.0, 1.0)
    log.info("         Done in %.1fs | mean=%.3f, std=%.3f", time.time() - t0, df["tfidf_similarity"].mean(), df["tfidf_similarity"].std())

    # ------------------------------------------------------------------
    # B. SENTENCE EMBEDDING SIMILARITY
    # ------------------------------------------------------------------
    log.info("  [2/4] Computing embedding similarity (this may take a while)...")
    t0 = time.time()

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(EMBEDDING_MODEL_NAME)

        BATCH_SIZE = 128
        log.info("         Encoding resumes...")
        resume_embs = model.encode(
            df["resume"].tolist(),
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        log.info("         Encoding job descriptions...")
        jd_embs = model.encode(
            df["job_description"].tolist(),
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        emb_sims = np.array([
            float(np.dot(resume_embs[i], jd_embs[i]))
            for i in range(n)
        ])
        df["embedding_similarity"] = np.clip(emb_sims, 0.0, 1.0)
        log.info("         Done in %.1fs | mean=%.3f, std=%.3f", time.time() - t0, df["embedding_similarity"].mean(), df["embedding_similarity"].std())

    except Exception as exc:
        log.warning("         Embedding model failed (%s). Using TF-IDF fallback.", exc)
        df["embedding_similarity"] = df["tfidf_similarity"] * 0.95  # deterministic fallback

    # ------------------------------------------------------------------
    # C. SKILL OVERLAP
    # ------------------------------------------------------------------
    log.info("  [3/4] Computing skill overlap...")
    t0 = time.time()

    SKILL_CATALOG = {
        "python", "java", "javascript", "typescript", "react", "vue", "angular",
        "node", "fastapi", "django", "flask", "spring", "docker", "kubernetes",
        "aws", "gcp", "azure", "sql", "nosql", "mongodb", "postgresql", "mysql",
        "machine learning", "deep learning", "nlp", "llm", "tensorflow", "pytorch",
        "scikit-learn", "airflow", "kubeflow", "git", "rest api", "graphql",
        "html", "css", "sass", "webpack", "redis", "kafka", "spark",
        "tableau", "power bi", "excel", "linux", "bash", "ci/cd", "jenkins",
        "terraform", "ansible", "agile", "scrum", "jira", "figma",
        "c++", "c#", "go", "rust", "ruby", "php", "swift", "kotlin",
    }

    def skill_overlap(resume_text: str, jd_text: str) -> float:
        r_skills = {s for s in SKILL_CATALOG if re.search(rf"\b{re.escape(s)}\b", resume_text)}
        j_skills = {s for s in SKILL_CATALOG if re.search(rf"\b{re.escape(s)}\b", jd_text)}
        if not j_skills:
            return 0.5  # neutral if JD has no recognisable skills
        return len(r_skills & j_skills) / len(j_skills)

    df["skill_overlap"] = [
        skill_overlap(r, j)
        for r, j in zip(df["resume"], df["job_description"])
    ]
    log.info("         Done in %.1fs | mean=%.3f", time.time() - t0, df["skill_overlap"].mean())

    # ------------------------------------------------------------------
    # D. LENGTH DIFFERENCE
    # ------------------------------------------------------------------
    log.info("  [4/4] Computing length difference...")
    r_len = df["resume"].str.len().astype(float)
    j_len = df["job_description"].str.len().astype(float)
    max_len = np.maximum(r_len, j_len).replace(0, 1)
    df["length_diff"] = np.abs(r_len - j_len) / max_len
    log.info("         Done | mean=%.3f", df["length_diff"].mean())

    # ------------------------------------------------------------------
    # E. ADVANCED FEATURES
    # ------------------------------------------------------------------
    log.info("  [5/5] Computing advanced features (sections, weights, experience, keywords)...")
    
    # E1. Section Similarity
    vectorizer_section = TfidfVectorizer(stop_words="english", max_features=1000)
    def compute_section_sim(r_sec, j_sec):
        if len(r_sec) < 10 or len(j_sec) < 10: return 0.0
        try:
            mat = vectorizer_section.fit_transform([r_sec, j_sec])
            return cosine_similarity(mat[0:1], mat[1:2])[0][0]
        except ValueError:
            return 0.0

    section_sims = []
    for r, j in zip(df["resume"], df["job_description"]):
        r_skills = extract_section(r, "skills")
        j_skills = extract_section(j, "skills")
        r_exp = extract_section(r, "experience")
        j_exp = extract_section(j, "experience")
        
        sim_s = compute_section_sim(r_skills, j_skills)
        sim_e = compute_section_sim(r_exp, j_exp)
        section_sims.append((sim_s + sim_e) / 2.0 if sim_s and sim_e else max(sim_s, sim_e))
    df["section_similarity"] = section_sims

    # E2. Weighted Skill Overlap
    df["weighted_skill_overlap"] = [weighted_skill_overlap(r, j) for r, j in zip(df["resume"], df["job_description"])]
    
    # E3. Experience Gap
    r_exps = [extract_experience(r) for r in df["resume"]]
    j_exps = [extract_experience(j) for j in df["job_description"]]
    df["experience_gap"] = [float(abs(r - j)) / max(j, 1) for r, j in zip(r_exps, j_exps)]
    
    # E4. Keyword Strength
    df["keyword_strength"] = [keyword_strength(r) for r in df["resume"]]

    # ------------------------------------------------------------------
    # FINAL FEATURE SET
    # ------------------------------------------------------------------
    feature_cols = [
        "tfidf_similarity", 
        "embedding_similarity", 
        "skill_overlap", 
        "length_diff",
        "weighted_skill_overlap",
        "experience_gap",
        "keyword_strength",
        "section_similarity"
    ]
    log.info("")
    log.info("  Final feature set: %s", feature_cols)
    log.info("  Feature statistics:")
    for col in feature_cols:
        log.info("    %-25s  mean=%.4f  std=%.4f  min=%.4f  max=%.4f",
                 col, df[col].mean(), df[col].std(), df[col].min(), df[col].max())

    return df, feature_cols, vectorizer


# ====================================================================
# STEP 7: MODEL TRAINING
# ====================================================================
def train_model(df, feature_cols: List[str]):
    """Train LogisticRegression + RandomForest on computed features."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    log.info("")
    log.info("=" * 60)
    log.info("STEP 7: MODEL TRAINING")
    log.info("=" * 60)

    if "label" not in df.columns:
        log.info("  No label column found. Skipping model training.")
        log.info("  Outputting similarity scores only.")
        return None, None, None, None

    X = df[feature_cols].values
    y = df["label"].values

    log.info("  Dataset: %d samples | %d positive | %d negative", len(y), (y == 1).sum(), (y == 0).sum())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    log.info("  Train: %d | Test: %d", len(X_train), len(X_test))

    # Scale features
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    from xgboost import XGBClassifier

    models = {
        "LogisticRegression": LogisticRegression(
            max_iter=1000,
            C=1.0,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_split=5,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            eval_metric="logloss"
        ),
    }

    results = {}
    best_model = None
    best_f1 = -1.0

    for name, model in models.items():
        log.info("")
        log.info("  Training: %s ...", name)
        t0 = time.time()
        
        # XGBoost handles sparse/numpy arrays.
        model.fit(X_train_s, y_train)
        elapsed = time.time() - t0

        metrics = evaluate_model(model, X_test_s, y_test, name)
        metrics["train_time_s"] = round(elapsed, 2)
        results[name] = metrics

        if metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            best_model = (name, model)

    # Feature Importance for XGBoost
    if "XGBoost" in models:
        xgb_model = models["XGBoost"]
        log.info("")
        log.info("  ┌─── XGBoost Feature Importance ───")
        importances = xgb_model.feature_importances_
        indices = np.argsort(importances)[::-1]
        for idx in indices:
            log.info("  │ %-25s : %.4f", feature_cols[idx], importances[idx])
        log.info("  └──────────────────────────────────")

    log.info("")
    log.info("  ★ Best model: %s (F1=%.4f)", best_model[0], best_f1)

    return results, best_model, scaler, (X_test_s, y_test)


# ====================================================================
# STEP 7 (cont): MODEL EVALUATION
# ====================================================================
def evaluate_model(model, X_test, y_test, name: str) -> Dict[str, float]:
    """Evaluate a trained classifier and print metrics."""
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    y_pred = model.predict(X_test)

    try:
        y_prob = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_prob)
    except Exception:
        auc = 0.0

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    log.info("  ┌─── %s Results ───", name)
    log.info("  │ Accuracy  : %.4f", acc)
    log.info("  │ Precision : %.4f", prec)
    log.info("  │ Recall    : %.4f", rec)
    log.info("  │ F1 Score  : %.4f", f1)
    log.info("  │ ROC-AUC   : %.4f", auc)
    log.info("  └───────────────────")

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(auc, 4),
    }


# ====================================================================
# STEP 8: OUTPUT SAMPLE
# ====================================================================
def output_sample(df, feature_cols: List[str], model_info=None, scaler=None):
    """Print sample rows with scores and predictions."""
    import pandas as pd

    log.info("")
    log.info("=" * 60)
    log.info("STEP 8: SAMPLE OUTPUT")
    log.info("=" * 60)

    sample = df.sample(n=min(5, len(df)), random_state=RANDOM_STATE).copy()

    display_cols = ["category", "position_title"] + feature_cols
    if "label" in sample.columns:
        display_cols.append("label")

    # Add model predictions if available
    if model_info is not None and scaler is not None:
        name, model = model_info
        X_sample = scaler.transform(sample[feature_cols].values)
        sample["prediction"] = model.predict(X_sample)
        try:
            sample["match_probability"] = np.round(model.predict_proba(X_sample)[:, 1] * 100, 1)
        except Exception:
            sample["match_probability"] = -1
        display_cols += ["prediction", "match_probability"]

    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 140)
    pd.set_option("display.float_format", lambda x: f"{x:.4f}")
    log.info("\n%s", sample[display_cols].to_string(index=False))


# ====================================================================
# STEP 9: SAVE ARTIFACTS
# ====================================================================
def save_artifacts(df, feature_cols, model_info, scaler, results, vectorizer):
    """Persist trained model, scaler, features, and metrics to disk."""
    import joblib

    log.info("")
    log.info("=" * 60)
    log.info("STEP 9: SAVING ARTIFACTS")
    log.info("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save feature data
    feature_path = OUTPUT_DIR / "features.csv"
    save_cols = ["category", "position_title"] + feature_cols
    if "label" in df.columns:
        save_cols.append("label")
    df[save_cols].to_csv(feature_path, index=False)
    log.info("  ✓ Features saved     -> %s", feature_path)

    if model_info is not None:
        name, model = model_info
        model_path = OUTPUT_DIR / "best_model.joblib"
        joblib.dump(model, model_path)
        log.info("  ✓ Model saved        -> %s (%s)", model_path, name)

    if scaler is not None:
        scaler_path = OUTPUT_DIR / "scaler.joblib"
        joblib.dump(scaler, scaler_path)
        log.info("  ✓ Scaler saved       -> %s", scaler_path)

    if vectorizer is not None:
        vectorizer_path = OUTPUT_DIR / "tfidf_vectorizer.joblib"
        joblib.dump(vectorizer, vectorizer_path)
        log.info("  ✓ TF-IDF saved       -> %s", vectorizer_path)

    if results is not None:
        metrics_path = OUTPUT_DIR / "metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        log.info("  ✓ Metrics saved      -> %s", metrics_path)

    log.info("")
    log.info("  All artifacts saved to: %s", OUTPUT_DIR)


# ====================================================================
# MAIN ENTRYPOINT
# ====================================================================
def main():
    log.info("")
    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║  RecruitIQ — ML Training Pipeline                      ║")
    log.info("╚══════════════════════════════════════════════════════════╝")
    log.info("")

    t_start = time.time()

    # Step 1
    datasets = load_data(DATA_DIR)

    # Step 2
    df = create_pairs(datasets)

    # Step 3
    df = preprocess(df)

    # Step 4-6
    df, feature_cols, vectorizer = feature_engineering(df)

    # Step 7
    results, model_info, scaler, test_data = train_model(df, feature_cols)

    # Step 8
    output_sample(df, feature_cols, model_info, scaler)

    # Step 9
    try:
        import joblib
        save_artifacts(df, feature_cols, model_info, scaler, results, vectorizer)
    except ImportError:
        log.warning("  joblib not available — skipping artifact save. Install with: pip install joblib")

    elapsed = time.time() - t_start
    log.info("")
    log.info("═" * 60)
    log.info("  Pipeline completed in %.1f seconds", elapsed)
    log.info("═" * 60)


if __name__ == "__main__":
    main()
