"""
User State Awareness - Heuristic-based state detection.

States: idle | busy | tired | stressed
Signals: time of day, message length, frequency, urgent language

NO LLM calls. NO background threads. Lazy reset via timestamp.
"""

import time
import re
from datetime import datetime
from typing import Literal, Dict, Any

from ..utils.stability_logger import log_flow

# Type alias for user states
UserState = Literal["idle", "busy", "tired", "stressed"]

# Singleton state tracker instance
_state_tracker = None


class UserStateTracker:
    """
    Lightweight heuristic-based user state tracker.
    
    - No persistent storage (ephemeral)
    - Resets lazily via timestamp comparison
    - Thread-safe (no shared mutable state beyond instance)
    """
    
    # Configuration constants
    RESET_TIMEOUT_SECONDS = 600  # 10 minutes idle = reset to 'idle'
    BUSY_MESSAGE_LENGTH = 200   # >200 chars = busy signal
    STRESSED_FREQUENCY_THRESHOLD = 3  # 3+ messages in 60s = stressed
    STRESSED_FREQUENCY_WINDOW = 60    # seconds
    
    # Urgent language patterns (case-insensitive)
    URGENT_PATTERNS = re.compile(
        r'\b(urgent|asap|emergency|help|hurry|quick|immediately|critical)\b',
        re.IGNORECASE
    )
    
    def __init__(self):
        self._current_state: UserState = "idle"
        self._last_interaction: float = 0.0
        self._message_timestamps: list = []  # Recent message times for frequency
        self._is_voice_mode: bool = False
    
    def update(self, message: str, is_voice: bool = False) -> UserState:
        """
        Update state based on new user interaction.
        Call this on every user message.
        Returns the new computed state.
        """
        now = time.time()
        current_hour = datetime.now().hour
        
        # Lazy reset: if idle too long, reset state
        if self._last_interaction > 0:
            idle_time = now - self._last_interaction
            if idle_time > self.RESET_TIMEOUT_SECONDS:
                self._current_state = "idle"
                self._message_timestamps.clear()
                log_flow("UserState", f"Reset to idle (was idle {idle_time:.0f}s)")
        
        self._last_interaction = now
        self._is_voice_mode = is_voice
        
        # Prune old timestamps (keep only last 60s)
        cutoff = now - self.STRESSED_FREQUENCY_WINDOW
        self._message_timestamps = [t for t in self._message_timestamps if t > cutoff]
        self._message_timestamps.append(now)
        
        # Compute new state based on signals
        new_state = self._compute_state(message, current_hour)
        
        if new_state != self._current_state:
            log_flow("UserState", f"Transition: {self._current_state} → {new_state}")
            self._current_state = new_state
        
        return self._current_state
    
    def _compute_state(self, message: str, hour: int) -> UserState:
        """
        Pure heuristic computation - no side effects.
        Priority: stressed > busy > tired > idle
        """
        # Signal 1: Urgent language → stressed
        if self.URGENT_PATTERNS.search(message):
            return "stressed"
        
        # Signal 2: High message frequency → stressed
        if len(self._message_timestamps) >= self.STRESSED_FREQUENCY_THRESHOLD:
            return "stressed"
        
        # Signal 3: Long message → busy
        if len(message) > self.BUSY_MESSAGE_LENGTH:
            return "busy"
        
        # Signal 4: Late night (23:00 - 06:00) → tired
        if hour >= 23 or hour < 6:
            return "tired"
        
        # Default: idle
        return "idle"
    
    def get_state(self) -> UserState:
        """Get current state (with lazy reset check)."""
        now = time.time()
        
        # Lazy reset on read
        if self._last_interaction > 0:
            idle_time = now - self._last_interaction
            if idle_time > self.RESET_TIMEOUT_SECONDS:
                self._current_state = "idle"
                self._message_timestamps.clear()
        
        return self._current_state
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get state as metadata dict for injection."""
        return {
            "user_state": self._current_state,
            "is_voice_mode": self._is_voice_mode,
            "last_interaction": self._last_interaction
        }
    
    def should_suppress_proactive(self) -> bool:
        """Returns True if proactive features should be suppressed."""
        return self._current_state == "stressed"


def get_user_state_tracker() -> UserStateTracker:
    """Singleton accessor for user state tracker."""
    global _state_tracker
    if _state_tracker is None:
        _state_tracker = UserStateTracker()
    return _state_tracker


def update_user_state(message: str, is_voice: bool = False) -> UserState:
    """Convenience function to update and get state."""
    return get_user_state_tracker().update(message, is_voice)


def get_current_user_state() -> UserState:
    """Convenience function to get current state."""
    return get_user_state_tracker().get_state()


def should_suppress_proactive() -> bool:
    """Check if proactive features should be suppressed."""
    return get_user_state_tracker().should_suppress_proactive()
