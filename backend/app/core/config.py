import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, Set, List

class Settings(BaseSettings):
    # API Keys & Security
    GROQ_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    # LLM Provider
    LLM_PROVIDER: str = "groq"
    LLM_TIMEOUT_SECONDS: int = 40
    LLM_MAX_TOKENS: int = 1100
    
    @property
    def groq_api_key(self) -> str:
        return self.GROQ_API_KEY
    
    # Model Configuration
    MODEL_DIR: str = "../pipeline/artifacts"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    LLM_MODEL: str = "llama-3.1-8b-instant"
    MAX_TEXT_LEN: int = 5000
    APP_ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "null"
    ]
    
    # 🎯 CATEGORIZED SKILL WEIGHTS (Systems Engineer Calibration)
    CORE_ML_SKILLS: Dict[str, float] = {
        "python": 1.0, "machine learning": 1.0, "ml": 1.0, "deep learning": 1.0,
        "scikit-learn": 1.0, "tensorflow": 1.0, "pytorch": 1.0, "nlp": 1.0, 
        "llm": 1.0, "feature engineering": 1.0, "ml core concepts": 1.0
    }
    SECONDARY_SKILLS: Dict[str, float] = {
        "fastapi": 0.6, "django": 0.6, "flask": 0.6, "api": 0.6, "sql": 0.6, "rest api": 0.6
    }
    INFRA_SKILLS: Dict[str, float] = {
        "docker": 0.5, "kubernetes": 0.5, "aws": 0.5, "gcp": 0.5, "azure": 0.5, "ci/cd": 0.5
    }
    
    @property
    def ALL_SKILL_WEIGHTS(self) -> Dict[str, float]:
        return {**self.CORE_ML_SKILLS, **self.SECONDARY_SKILLS, **self.INFRA_SKILLS}
    
    # Global Skill Catalog (Expanded for Precision Capture)
    SKILL_CATALOG: Set[str] = {
        "python", "java", "javascript", "typescript", "react", "vue", "angular",
        "node", "fastapi", "django", "flask", "spring", "docker", "kubernetes",
        "aws", "gcp", "azure", "sql", "nosql", "mongodb", "postgresql", "mysql",
        "machine learning", "deep learning", "nlp", "llm", "tensorflow", "pytorch",
        "scikit-learn", "airflow", "kubeflow", "git", "rest api", "graphql",
        "html", "css", "sass", "webpack", "redis", "kafka", "spark",
        "tableau", "power bi", "excel", "linux", "bash", "ci/cd", "jenkins",
        "terraform", "ansible", "agile", "scrum", "jira", "figma",
        "c++", "c#", "go", "rust", "ruby", "php", "swift", "kotlin", "ml", "ai", 
        "artificial intelligence", "data science", "data engineering", "big data",
        "pyspark", "snowflake", "dbt", "databricks", "hadoop", "hive", "oracle",
        "redshift", "athena", "lambda", "s3", "ec2", "ecs", "eks", "fargate",
        "serverless", "microservices", "kafka", "rabbitmq", "grpc", "protobuf",
        "cypress", "jest", "selenium", "tDD", "bDD", "cypress", "playwright",
        "opencv", "spacy", "nltk", "huggingface", "langchain", "llama", "bedrock",
        "openstack", "vagrant", "nomad", "traefik", "nginx", "apache", "solr",
        "elasticsearch", "kibana", "grafana", "prometheus", "sentry", "new relic",
        "perl", "fortran", "matlab", "r", "julia", "lua", "scala", "elixir",
        "erlang", "clojure", "dart", "flutter", "react native", "ionic", "cordova",
        "nextjs", "nuxtjs", "tailwind", "bootstrap", "material ui", "nestjs",
        "svelte", "solidjs", "alpinejs", "remix", "gatsby", "redux", "mobx",
        "zod", "prettier", "eslint", "vite", "parcel", "rollup", "esbuild"
    }

    # Deterministic Feature Schema (Rule 7)
    FEATURE_ORDER: List[str] = [
        "tfidf_score",
        "embedding_score",
        "skill_overlap",
        "experience_gap",
        "keyword_strength",
        "section_similarity"
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    return Settings()
