"""
Memory Optimization Metrics Endpoint

Provides /metrics endpoint for monitoring:
- RSS memory usage
- Model load status
- Rate limit stats
- Cache hit rates
"""
import os
import gc
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_memory_stats() -> Dict[str, Any]:
    """Get current memory statistics."""
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        
        return {
            "rss_mb": mem_info.rss / 1024**2,
            "vms_mb": mem_info.vms / 1024**2,
            "percent": process.memory_percent()
        }
    except ImportError:
        return {"error": "psutil not installed"}

def get_model_status() -> Dict[str, Any]:
    """Get status of loaded models."""
    status = {}
    
    # FAISS embeddings
    try:
        from ..memory.faiss_store import get_memory_store
        store = get_memory_store()
        status["faiss_embeddings_loaded"] = store._embeddings_model is not None
        status["faiss_mmap_active"] = getattr(store, '_mmap_active', False)
        status["faiss_vectors"] = store.faiss_index.ntotal if store.faiss_index else 0
        status["history_in_memory"] = len(store.conversation_history)
    except Exception as e:
        status["faiss_error"] = str(e)
    
    # Chroma embeddings
    try:
        from ..memory.chroma_store.model import is_loaded
        status["chroma_embeddings_loaded"] = is_loaded()
    except Exception as e:
        status["chroma_error"] = str(e)
    
    # Kokoro TTS
    try:
        from .tts import _pipeline
        status["kokoro_loaded"] = _pipeline is not None
    except:
        pass
    
    return status

def get_rate_limit_status() -> Dict[str, Any]:
    """Get rate limit and circuit breaker status."""
    try:
        from .rate_limiter import get_rate_limit_stats
        return get_rate_limit_stats()
    except:
        return {}

def get_all_metrics() -> Dict[str, Any]:
    """Aggregate all metrics."""
    return {
        "memory": get_memory_stats(),
        "models": get_model_status(),
        "rate_limits": get_rate_limit_status(),
        "gc": {
            "objects": len(gc.get_objects()),
            "garbage": len(gc.garbage)
        }
    }


def get_memory_viewer_data() -> Dict[str, Any]:
    """Get memory viewer data for debugging."""
    try:
        from .memory_manager import get_memory_viewer_data as get_viewer, get_advanced_memory_stats
        return {
            "memories": get_viewer(limit=50),
            "stats": get_advanced_memory_stats()
        }
    except Exception as e:
        return {"error": str(e)}


class MetricsHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for /metrics and /memory-viewer endpoints."""
    
    def do_GET(self):
        if self.path == "/metrics" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            metrics = get_all_metrics()
            self.wfile.write(json.dumps(metrics, indent=2).encode())
        
        elif self.path == "/memory-viewer":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            viewer_data = get_memory_viewer_data()
            self.wfile.write(json.dumps(viewer_data, indent=2).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress logging
        pass


_metrics_server = None

def start_metrics_server(port: int = 9090):
    """Start metrics HTTP server in background thread."""
    global _metrics_server
    
    if _metrics_server is not None:
        return
    
    try:
        _metrics_server = HTTPServer(("127.0.0.1", port), MetricsHandler)
        thread = threading.Thread(target=_metrics_server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"📊 Metrics server started on http://127.0.0.1:{port}/metrics")
        print(f"📊 Metrics server started on http://127.0.0.1:{port}/metrics")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")

def stop_metrics_server():
    """Stop metrics server."""
    global _metrics_server
    if _metrics_server:
        _metrics_server.shutdown()
        _metrics_server = None
