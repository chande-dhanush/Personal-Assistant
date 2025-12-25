"""
Task Continuity - Lightweight task follow-up intelligence.

Tracks: pending | in_progress | stalled
Uses ephemeral storage (task_metadata.json) - not user preferences.
Trigger: Morning routine checks for stalled tasks.

NO background threads. NO reminders spam.
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from ..utils.stability_logger import log_flow
from ..config import get_project_root

# Ephemeral storage path (assistant-internal, not user-visible)
TASK_METADATA_FILE = os.path.join(get_project_root(), "data", "task_metadata.json")

# Task is stalled if pending for more than this
STALLED_THRESHOLD_HOURS = 24

# Stop offering follow-ups after this many ignores
MAX_FOLLOWUP_OFFERS = 2


class TaskTracker:
    """
    Tracks task states and follow-up attempts.
    
    Uses ephemeral JSON storage that is:
    - Assistant-internal only
    - Disposable (can be deleted without data loss)
    - Not shown to user
    """
    
    def __init__(self):
        self._metadata: Dict[str, Any] = {}
        self._load()
    
    def _load(self):
        """Load metadata from file if exists."""
        try:
            if os.path.exists(TASK_METADATA_FILE):
                with open(TASK_METADATA_FILE, 'r', encoding='utf-8') as f:
                    self._metadata = json.load(f)
        except Exception as e:
            log_flow("TaskTracker", f"Load failed: {e}, starting fresh")
            self._metadata = {}
    
    def _save(self):
        """Persist metadata to file."""
        try:
            os.makedirs(os.path.dirname(TASK_METADATA_FILE), exist_ok=True)
            with open(TASK_METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            log_flow("TaskTracker", f"Save failed: {e}")
    
    def track_task(self, task_title: str, created_time: Optional[str] = None):
        """
        Start tracking a task. Called when a task is created.
        """
        task_id = self._normalize_id(task_title)
        
        if task_id not in self._metadata:
            self._metadata[task_id] = {
                "title": task_title,
                "created_at": created_time or datetime.now().isoformat(),
                "status": "pending",
                "followup_count": 0,
                "last_followup": None
            }
            self._save()
            log_flow("TaskTracker", f"Tracking new task: {task_title}")
    
    def mark_in_progress(self, task_title: str):
        """Mark a task as in progress (stops follow-ups)."""
        task_id = self._normalize_id(task_title)
        if task_id in self._metadata:
            self._metadata[task_id]["status"] = "in_progress"
            self._save()
    
    def mark_completed(self, task_title: str):
        """Remove task from tracking when completed."""
        task_id = self._normalize_id(task_title)
        if task_id in self._metadata:
            del self._metadata[task_id]
            self._save()
            log_flow("TaskTracker", f"Task completed and untracked: {task_title}")
    
    def record_followup_offered(self, task_title: str):
        """Record that a follow-up was offered for this task."""
        task_id = self._normalize_id(task_title)
        if task_id in self._metadata:
            self._metadata[task_id]["followup_count"] += 1
            self._metadata[task_id]["last_followup"] = datetime.now().isoformat()
            self._save()
    
    def get_stalled_tasks(self) -> List[Dict[str, Any]]:
        """
        Get tasks that are stalled (pending > 24h) and haven't been
        followed up too many times.
        """
        stalled = []
        now = datetime.now()
        
        for task_id, data in self._metadata.items():
            # Skip if already in progress
            if data.get("status") != "pending":
                continue
            
            # Skip if followed up too many times
            if data.get("followup_count", 0) >= MAX_FOLLOWUP_OFFERS:
                continue
            
            # Check if stalled (pending > threshold)
            try:
                created = datetime.fromisoformat(data["created_at"])
                age = now - created
                
                if age > timedelta(hours=STALLED_THRESHOLD_HOURS):
                    stalled.append({
                        "title": data["title"],
                        "age_hours": age.total_seconds() / 3600,
                        "followup_count": data.get("followup_count", 0)
                    })
            except (ValueError, KeyError):
                continue
        
        return stalled
    
    def sync_with_google_tasks(self, google_tasks: List[Dict[str, Any]]):
        """
        Sync our tracking with Google Tasks.
        Called when tasks_list is invoked.
        """
        for task in google_tasks:
            title = task.get("title", "")
            if not title:
                continue
            
            task_id = self._normalize_id(title)
            
            # If task exists in Google but not tracked, start tracking
            if task_id not in self._metadata:
                self.track_task(title, task.get("updated"))
    
    def _normalize_id(self, title: str) -> str:
        """Normalize task title to ID."""
        return title.lower().strip().replace(" ", "_")[:50]
    
    def cleanup_old(self, days: int = 30):
        """Remove tracking data older than N days."""
        now = datetime.now()
        to_remove = []
        
        for task_id, data in self._metadata.items():
            try:
                created = datetime.fromisoformat(data["created_at"])
                if (now - created).days > days:
                    to_remove.append(task_id)
            except:
                continue
        
        for task_id in to_remove:
            del self._metadata[task_id]
        
        if to_remove:
            self._save()
            log_flow("TaskTracker", f"Cleaned up {len(to_remove)} old entries")


# Singleton
_tracker = None


def get_task_tracker() -> TaskTracker:
    """Singleton accessor for task tracker."""
    global _tracker
    if _tracker is None:
        _tracker = TaskTracker()
    return _tracker


def get_stalled_tasks() -> List[Dict[str, Any]]:
    """Convenience function to get stalled tasks."""
    return get_task_tracker().get_stalled_tasks()


def record_followup_offered(task_title: str):
    """Record that we offered a follow-up for this task."""
    get_task_tracker().record_followup_offered(task_title)
