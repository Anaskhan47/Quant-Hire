import time
import logging
from collections import deque
from typing import Dict, Any, List

log = logging.getLogger("backend.metrics")

class MetricsTracker:
    def __init__(self, window_size: int = 100):
        self.latencies = deque(maxlen=window_size)
        self.success_count = 0
        self.error_count = 0
        self.fallback_llm_count = 0
        self.fallback_emb_count = 0
        self.total_requests = 0

    def record_request(self, duration_ms: float, success: bool, llm_fallback: bool = False, emb_fallback: bool = False):
        self.total_requests += 1
        self.latencies.append(duration_ms)
        if success: self.success_count += 1
        else: self.error_count += 1
        
        if llm_fallback: self.fallback_llm_count += 1
        if emb_fallback: self.fallback_emb_count += 1

    def get_stats(self) -> Dict[str, Any]:
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        p95_latency = sorted(list(self.latencies))[int(len(self.latencies) * 0.95)] if self.latencies else 0
        
        return {
            "request_success_rate": round((self.success_count / self.total_requests) * 100, 2) if self.total_requests > 0 else 100.0,
            "error_rate": round((self.error_count / self.total_requests) * 100, 2) if self.total_requests > 0 else 0.0,
            "fallback_rate_llm": round((self.fallback_llm_count / self.total_requests) * 100, 2) if self.total_requests > 0 else 0.0,
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "total_requests": self.total_requests
        }

metrics = MetricsTracker()
