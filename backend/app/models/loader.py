import logging
import joblib
from pathlib import Path
from typing import Optional, Any
from sentence_transformers import SentenceTransformer
from ..core.config import settings

log = logging.getLogger("backend.models")

class ModelSingleton:
    _instance: Optional["ModelSingleton"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelSingleton, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.ml_model: Optional[Any] = None
        self.scaler: Optional[Any] = None
        self.tfidf: Optional[Any] = None
        self.emb_model: Optional[SentenceTransformer] = None
        
        self.load_artifacts()
        self._initialized = True

    def load_artifacts(self):
        """Loads ML artifacts and SentenceTransformers synchronously at startup."""
        # Note: artifacts are assumed to be relative to the workspace root
        base_path = Path(settings.MODEL_DIR)
        
        try:
            if (base_path / "best_model.joblib").exists():
                self.ml_model = joblib.load(base_path / "best_model.joblib")
                self.scaler = joblib.load(base_path / "scaler.joblib")
                log.info("Successfully loaded XGBoost model and Scaler")
        except Exception as e:
            log.warning(f"Could not load ML artifacts: {e}. Fallback score will be used.")

        try:
            self.emb_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            log.info(f"Successfully loaded {settings.EMBEDDING_MODEL} singleton")
        except Exception as e:
            log.error(f"CRITICAL: Failed to load embedding model: {e}")

model_loader = ModelSingleton()
