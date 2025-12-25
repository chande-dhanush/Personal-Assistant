"""
Proactive Routines - Morning Briefing & Evening Summary.

CRITICAL: Routines emit PRE-RENDERED assistant messages.
They NEVER go through Router/Planner/Executor.
"""

import datetime
import os
from typing import Dict, Any, Optional

from ..utils.preferences import user_preferences, update_preference
from ..utils.stability_logger import log_flow, log_warning
from ..config import get_project_root

# Lazy import tools to avoid circular deps
def _get_tools():
    from ..core.tools import (
        calendar_get_events, tasks_list, web_search, 
        note_create, get_system_info
    )
    return calendar_get_events, tasks_list, web_search, note_create, get_system_info


class RoutineManager:
    """
    Manages proactive daily routines.
    
    RULE: Routines return FINAL assistant text, not LLM instructions.
    """
    def __init__(self):
        pass

    def check_morning_trigger(self) -> bool:
        """
        Returns True if morning routine should run.
        Conditions: 8-11 AM AND hasn't run today.
        """
        now = datetime.datetime.now()
        current_hour = now.hour
        
        # TIME WINDOW CHECK: Only run between 8 AM and 11 AM
        if not (8 <= current_hour < 11):
            return False

        today_str = datetime.date.today().isoformat()
        last_run = user_preferences.preferences.get("system_settings", {}).get("last_morning_run")
        
        return last_run != today_str

    def mark_morning_complete(self):
        """Updates the last run date to today."""
        today_str = datetime.date.today().isoformat()
        update_preference("system_settings", "last_morning_run", today_str)

    def run_morning_routine(self) -> Dict[str, Any]:
        """
        Generate morning briefing as a FINAL assistant message.
        Returns dict ready to emit via ViewModel signal.
        
        DOES NOT go through LLM pipeline.
        """
        log_flow("ROUTINE", "Morning routine started")
        self.mark_morning_complete()
        
        calendar_get_events, tasks_list, web_search, _, get_system_info = _get_tools()
        
        # 1. Get Date/Time
        try:
            now = datetime.datetime.now()
            day_name = now.strftime("%A")
            date_str = now.strftime("%B %d, %Y")
            time_str = now.strftime("%I:%M %p")
            sys_info = f"It's {day_name}, {date_str} - {time_str}"
        except Exception as e:
            sys_info = "Today"
            log_warning(f"System info failed: {e}")
        
        # 2. Get Calendar
        cal_summary = "No events scheduled today."
        try:
            cal_events = calendar_get_events.invoke({})
            if cal_events and "No events" not in str(cal_events):
                # Parse and summarize
                cal_summary = str(cal_events)[:300]
        except Exception as e:
            log_warning(f"Calendar failed: {e}")
        
        # 3. Get Tasks
        tasks_summary = "No pending tasks."
        try:
            tasks = tasks_list.invoke({})
            if tasks and "No tasks" not in str(tasks):
                tasks_summary = str(tasks)[:200]
        except Exception as e:
            log_warning(f"Tasks failed: {e}")
        
        # 4. Get AI News (Tavily) with explicit validation
        news_summary = ""
        try:
            # Validate Tavily key exists
            tavily_key = os.getenv("TAVILY_API_KEY")
            if not tavily_key:
                log_warning("Tavily key missing — skipping AI news")
            else:
                news_result = web_search.invoke({"query": "latest AI news headlines today"})
                if news_result and len(str(news_result)) > 20:
                    # Extract first few headlines
                    news_summary = f"\n\n📰 **AI News:** {str(news_result)[:200]}..."
                    log_flow("ROUTINE_NEWS", f"Results: {len(str(news_result))} chars")
                else:
                    log_flow("ROUTINE_NEWS", "No news results")
        except Exception as e:
            log_warning(f"AI news fetch failed: {e}")
        
        # 5. Check for stalled tasks (Task Continuity)
        stalled_note = ""
        try:
            from ..utils.task_tracker import get_stalled_tasks, record_followup_offered
            from ..utils.user_state import should_suppress_proactive
            
            # Skip if user is stressed
            if not should_suppress_proactive():
                stalled = get_stalled_tasks()
                if stalled:
                    first = stalled[0]
                    stalled_note = f"\n\n⏰ By the way, '{first['title']}' has been pending for a while. Want to tackle it today?"
                    record_followup_offered(first['title'])
        except Exception:
            pass

        # 6. Build FINAL pre-rendered message (no LLM needed)
        greeting = self._get_greeting()
        
        message = (
            f"{greeting}\n\n"
            f"📅 **{sys_info}**\n\n"
            f"**Your Schedule:**\n{cal_summary}\n\n"
            f"**Pending Tasks:**\n{tasks_summary}"
            f"{news_summary}"
            f"{stalled_note}"
        )
        
        log_flow("ROUTINE", "Morning routine complete")
        
        # Return as ready-to-emit payload
        return {
            "content": message,
            "metadata": {
                "mode": "Routine",
                "routine_type": "morning",
                "mood": "Neutral"
            }
        }
    
    def _get_greeting(self) -> str:
        """Get time-appropriate greeting."""
        hour = datetime.datetime.now().hour
        if hour < 12:
            return "☀️ Good morning!"
        elif hour < 17:
            return "🌤️ Good afternoon!"
        else:
            return "🌙 Good evening!"

    def check_evening_trigger(self) -> bool:
        """Returns True if evening routine should run (after 11 PM)."""
        now = datetime.datetime.now()
        current_hour = now.hour
        
        if current_hour < 23:
            return False

        today_str = datetime.date.today().isoformat()
        last_run = user_preferences.preferences.get("system_settings", {}).get("last_evening_run")
        
        return last_run != today_str

    def mark_evening_complete(self):
        """Updates the last evening run date to today."""
        today_str = datetime.date.today().isoformat()
        update_preference("system_settings", "last_evening_run", today_str)

    def run_evening_routine(self) -> Dict[str, Any]:
        """
        Generate evening summary as a FINAL assistant message.
        Returns dict ready to emit via ViewModel signal.
        """
        log_flow("ROUTINE", "Evening routine started")
        self.mark_evening_complete()
        
        calendar_get_events, tasks_list, _, note_create, _ = _get_tools()
        
        # 1. Get Tomorrow's Calendar
        tomorrow_summary = "No events scheduled."
        try:
            tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
            cal_events = calendar_get_events.invoke({"date": tomorrow})
            if cal_events and "No events" not in str(cal_events):
                tomorrow_summary = str(cal_events)[:200]
        except Exception as e:
            log_warning(f"Tomorrow calendar failed: {e}")
        
        # 2. Get Tasks
        tasks_summary = ""
        try:
            tasks = tasks_list.invoke({})
            if tasks and "No tasks" not in str(tasks):
                tasks_summary = f"\n\n**Outstanding Tasks:**\n{str(tasks)[:150]}"
        except Exception:
            pass
        
        # 3. Create Daily Log Note
        log_note = ""
        try:
            date_str = datetime.date.today().isoformat()
            note_title = f"Daily Log - {date_str}"
            note_content = f"Session ended at {datetime.datetime.now().strftime('%H:%M')}."
            note_create.invoke({"title": note_title, "content": note_content, "folder": "daily"})
            log_note = f"\n\n✅ Daily log saved to notes."
        except Exception:
            pass
        
        # 4. Build FINAL pre-rendered message
        message = (
            f"🌙 Wrapping up for the day.\n\n"
            f"**Tomorrow's Schedule:**\n{tomorrow_summary}"
            f"{tasks_summary}"
            f"{log_note}\n\n"
            f"Rest well! 💤"
        )
        
        log_flow("ROUTINE", "Evening routine complete")
        
        return {
            "content": message,
            "metadata": {
                "mode": "Routine",
                "routine_type": "evening",
                "mood": "Neutral"
            }
        }


# Global Instance
routine_manager = RoutineManager()


def get_routine_message_if_triggered() -> Optional[Dict[str, Any]]:
    """
    Check if any routine should run and return the message payload.
    Returns None if no routine triggered.
    
    Called by ViewModel before agent processing.
    """
    from ..utils.user_state import should_suppress_proactive
    
    # Don't run routines if user is stressed
    if should_suppress_proactive():
        return None
    
    if routine_manager.check_morning_trigger():
        return routine_manager.run_morning_routine()
    
    if routine_manager.check_evening_trigger():
        return routine_manager.run_evening_routine()
    
    return None
