import re
from typing import List, Set


SKILL_CATALOG = {
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "vue",
    "node",
    "fastapi",
    "django",
    "flask",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "sql",
    "nosql",
    "mongodb",
    "postgresql",
    "machine learning",
    "deep learning",
    "nlp",
    "llm",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "airflow",
    "kubeflow",
    "git",
    "rest api",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def extract_skills(text: str) -> List[str]:
    text_norm = normalize(text)
    found: Set[str] = set()
    for skill in SKILL_CATALOG:
        if re.search(rf"\b{re.escape(skill)}\b", text_norm):
            found.add(skill)
    return sorted(found)


def extract_years(text: str) -> int:
    text_norm = normalize(text)
    patterns = [
        r"(\d+)\+?\s*years?",
        r"(\d+)\+?\s*yrs?",
    ]
    nums = []
    for pattern in patterns:
        nums.extend(int(m) for m in re.findall(pattern, text_norm))
    return max(nums) if nums else 0
