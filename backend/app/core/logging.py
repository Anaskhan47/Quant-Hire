import json
import logging
import sys
from datetime import datetime, timezone

from app.middleware.request_context import get_request_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)
