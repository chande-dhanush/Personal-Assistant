"""
Yuki V4 Reliability Watch Mode - Stability Logger

Logs system events for 24-hour monitoring.
No functional changes - observation only.
"""
import os
import json
import logging
import atexit
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Log file path
LOG_DIR = Path(__file__).parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")
STABILITY_LOG_FILE = LOG_DIR / f"stability_{TODAY}.log"

# Health counters
_health = {
    "errors": 0,
    "warnings": 0,
    "success_calls": 0,
    "flow_events": 0,
    "mem_events": 0,
    "ctx_events": 0
}

# Configure stability logger
stability_logger = logging.getLogger("yuki.stability")
stability_logger.setLevel(logging.DEBUG)

# File handler
file_handler = logging.FileHandler(STABILITY_LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
))
stability_logger.addHandler(file_handler)

# Console handler (minimal)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('[WATCH] %(message)s'))
stability_logger.addHandler(console_handler)


def log_flow(stage: str, details: str = ""):
    """Log message flow events."""
    global _health
    _health["flow_events"] += 1
    stability_logger.debug(f"[FLOW] {stage} | {details}")


def log_mem(action: str, data: Dict[str, Any] = None):
    """Log memory events."""
    global _health
    _health["mem_events"] += 1
    if data:
        short_content = str(data.get('content', ''))[:50] if data else ''
        stability_logger.debug(f"[MEM] {action} | role={data.get('role', 'unknown')} | content={short_content}...")
    else:
        stability_logger.debug(f"[MEM] {action}")


def log_reinforce(idx: int, new_score: float):
    """Log memory reinforcement."""
    stability_logger.debug(f"[MEM] REINFORCE idx={idx} new_score={new_score:.4f}")


def log_ctx(summary_len: int, raw_count: int, memory_count: int):
    """Log context building stats."""
    global _health
    _health["ctx_events"] += 1
    stability_logger.debug(f"[CTX] summary_len={summary_len} raw_msgs={raw_count} memory_snippets={memory_count}")


def log_router(decision: str, reason: str = ""):
    """Log router decisions."""
    stability_logger.info(f"[ROUTER] {decision} | {reason}")


def log_success():
    """Log successful LLM call."""
    global _health
    _health["success_calls"] += 1


def log_warning(msg: str):
    """Log warning."""
    global _health
    _health["warnings"] += 1
    stability_logger.warning(msg)


def log_error(msg: str):
    """Log error."""
    global _health
    _health["errors"] += 1
    stability_logger.error(msg)


def get_health_report() -> Dict[str, int]:
    """Get current health counters."""
    return _health.copy()


def _write_health_report_on_exit():
    """Write health report to log on exit."""
    report = get_health_report()
    stability_logger.info("=" * 50)
    stability_logger.info("HEALTH REPORT ON EXIT")
    stability_logger.info(f"  Errors: {report['errors']}")
    stability_logger.info(f"  Warnings: {report['warnings']}")
    stability_logger.info(f"  Success Calls: {report['success_calls']}")
    stability_logger.info(f"  Flow Events: {report['flow_events']}")
    stability_logger.info(f"  Memory Events: {report['mem_events']}")
    stability_logger.info(f"  Context Events: {report['ctx_events']}")
    stability_logger.info("=" * 50)
    
    # Also write JSON report
    report_file = LOG_DIR / f"health_report_{TODAY}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)


# Register exit handler
atexit.register(_write_health_report_on_exit)

# Log startup
stability_logger.info(f"Reliability Watch Mode started - {datetime.now().isoformat()}")
