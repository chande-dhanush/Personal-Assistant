import time
import threading
import datetime
import psutil
import gc
from PyQt5.QtCore import QObject, pyqtSignal

from ..core.tools import calendar_get_events, get_google_creds
from googleapiclient.discovery import build
from .routines import routine_manager

class AgentScheduler(QObject):
    """
    Background scheduler for 'Agentic' behaviors.
    - Meeting Nudges (10m before)
    - Health Monitor (RAM/Late Night)
    - Proactive Routines (Morning/Evening)
    """
    alert_triggered = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.events_cache = []
        self.last_cache_update = 0
        self.cache_interval = 10200 # Update cache every 3 hour (approx)
        self.notified_event_ids = set()
        
    def start(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()
        print("🕰️ Agent Scheduler Started")

    def stop(self):
        self.running = False

    def _loop(self):
        print("🕰️ Scheduler Loop Active")
        while self.running:
            try:
                now = time.time()
                
                # 1. Update Calendar Cache
                if now - self.last_cache_update > self.cache_interval:
                    self._refresh_calendar_cache()

                # 2. Check for Nudges
                self._check_meeting_nudge()

                # 3. Check Health
                self._check_health()
                
                # 4. Check Proactive Routines (Morning/Evening)
                self._check_routines()
                
                time.sleep(60) 
            except Exception as e:
                print(f"⚠️ Scheduler Error inside loop: {e}")
                time.sleep(60)

    def _check_routines(self):
        """Check if Morning/Evening routines should fire."""
        try:
            # Morning Routine (8-11 AM)
            if routine_manager.check_morning_trigger():
                msg = routine_manager.run_morning_routine()
                # Wrap in brief text for TTS
                self.alert_triggered.emit(msg)
                
            # Evening Routine (11 PM+)
            if routine_manager.check_evening_trigger():
                msg = routine_manager.run_evening_routine()
                self.alert_triggered.emit(msg)
        except Exception as e:
            print(f"⚠️ Routine Check Failed: {e}")

    def _refresh_calendar_cache(self):
        """Fetch today's remaining events."""
        try:
            creds = get_google_creds()
            if not creds: return

            service = build('calendar', 'v3', credentials=creds)
            
            events_result = service.events().list(
                calendarId='primary', 
                timeMin=datetime.datetime.utcnow().isoformat() + 'Z',
                maxResults=20, 
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            self.events_cache = events_result.get('items', [])
            self.last_cache_update = time.time()
            
        except Exception as e:
            print(f"⚠️ Scheduler Cache Update Failed: {e}")

    def _check_meeting_nudge(self):
        """Check if any event is starting in ~10 mins."""
        now = datetime.datetime.now().astimezone() # Local aware
        
        for event in self.events_cache:
            eid = event['id']
            if eid in self.notified_event_ids: continue
            
            start = event['start'].get('dateTime')
            if not start: continue # All day event
            
            try:
                event_time = datetime.datetime.fromisoformat(start)
                delta = (event_time - now).total_seconds()
                
                # Window: 0 to 11 minutes (Catch-up if app started late)
                if 0 < delta <= 660:
                    # VERIFY existence (API Call) - "Timer checks if event exists"
                    if self._verify_event_exists(eid):
                        summary = event.get('summary', 'Meeting')
                        mins_left = int(delta / 60)
                        msg = f"🔔 Reminder: '{summary}' starts in {mins_left} minutes."
                        self.alert_triggered.emit(msg)
                        self.notified_event_ids.add(eid)
            except Exception as e:
                pass

    def _verify_event_exists(self, event_id):
        """Confirm event wasn't cancelled."""
        try:
            creds = get_google_creds()
            service = build('calendar', 'v3', credentials=creds)
            service.events().get(calendarId='primary', eventId=event_id).execute()
            return True
        except:
            return False

    def _check_health(self):
        """Check RAM and late night activity."""
        # Memory Protection (Target: 90%)
        mem = psutil.virtual_memory()
        if mem.percent > 90:
            print(f"⚠️ High Memory Usage ({mem.percent}%). Cleaning up...")
            gc.collect()
            
            # Optional: Aggressively clear large caches if critical
            if mem.percent > 95:
                print("🚨 Critical RAM. Forcing garbage collection.")
                self.events_cache = [] # clear cache
                
        now = datetime.datetime.now()
        # Only trigger at exactly 2 AM to avoid spam (if loop hits that minute)
        # Using a guard variable would be better but simple check is okay for now if loop is 60s
        if now.hour == 2 and now.minute == 0:
             self.alert_triggered.emit("🌙 It's 2 AM. You've been working hard. Maybe time for a break?")
