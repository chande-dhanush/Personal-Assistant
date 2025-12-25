"""
P1 Rate Limiting and Circuit Breaker for LLM Calls

Provides:
- Rate limiting per model (max concurrent calls)
- Circuit breaker for RESOURCE_EXHAUSTED errors
- Fallback escalation
"""
import time
import threading
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Circuit breaker for external API calls.
    Opens on repeated failures, auto-closes after cooldown.
    """
    def __init__(self, failure_threshold: int = 3, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def record_success(self):
        with self._lock:
            self.failures = 0
            self.state = "CLOSED"
    
    def record_failure(self, error: Exception = None):
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit OPEN after {self.failures} failures")
    
    def allow_request(self) -> bool:
        with self._lock:
            if self.state == "CLOSED":
                return True
            
            if self.state == "OPEN":
                # Check if cooldown has passed
                if time.time() - self.last_failure_time > self.reset_timeout:
                    self.state = "HALF_OPEN"
                    return True
                return False
            
            # HALF_OPEN - allow one request to test
            return self.state == "HALF_OPEN"


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    """
    def __init__(self, max_calls: int = 10, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self._lock = threading.Lock()
    
    def acquire(self, timeout: float = 5.0) -> bool:
        """Try to acquire a slot. Returns True if successful."""
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            with self._lock:
                now = time.time()
                # Remove old calls outside the period
                self.calls = [t for t in self.calls if now - t < self.period]
                
                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return True
            
            time.sleep(0.1)
        
        return False


# Global instances per model type
_breakers = {}
_limiters = {}
_global_lock = threading.Lock()

def get_circuit_breaker(model_name: str) -> CircuitBreaker:
    """Get or create circuit breaker for a model."""
    with _global_lock:
        if model_name not in _breakers:
            _breakers[model_name] = CircuitBreaker()
        return _breakers[model_name]

def get_rate_limiter(model_name: str, max_calls: int = 5) -> RateLimiter:
    """Get or create rate limiter for a model."""
    with _global_lock:
        if model_name not in _limiters:
            _limiters[model_name] = RateLimiter(max_calls=max_calls)
        return _limiters[model_name]


def with_rate_limit(model_name: str, max_calls: int = 5):
    """Decorator to add rate limiting and circuit breaker to LLM calls."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker(model_name)
            limiter = get_rate_limiter(model_name, max_calls)
            
            # Check circuit breaker
            if not breaker.allow_request():
                logger.warning(f"Circuit OPEN for {model_name}, skipping call")
                raise Exception(f"Circuit breaker OPEN for {model_name}")
            
            # Rate limiting
            if not limiter.acquire(timeout=5.0):
                logger.warning(f"Rate limit exceeded for {model_name}")
                raise Exception(f"Rate limit exceeded for {model_name}")
            
            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                error_str = str(e).lower()
                if "resource_exhausted" in error_str or "quota" in error_str or "rate" in error_str:
                    logger.warning(f"Resource exhausted for {model_name}: {e}")
                    breaker.record_failure(e)
                raise
        
        return wrapper
    return decorator


def get_rate_limit_stats() -> dict:
    """Get current rate limiting stats for metrics."""
    stats = {}
    with _global_lock:
        for name, breaker in _breakers.items():
            stats[name] = {
                "state": breaker.state,
                "failures": breaker.failures,
                "calls_in_window": len(_limiters.get(name, RateLimiter()).calls)
            }
    return stats
