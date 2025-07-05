import psutil
import datetime
import random
from datetime import datetime, timedelta

def get_system_info():
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return f"CPU: {cpu}%, Memory: {mem}%, Disk: {disk}%"

def get_current_time():
    return datetime.now().strftime('%I:%M %p')

def get_current_date():
    return datetime.datetime.now().strftime('%B %d, %Y') 