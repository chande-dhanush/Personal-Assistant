import psutil
import datetime

def get_system_info():
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return f"CPU: {cpu}%, Memory: {mem}%, Disk: {disk}%"

def get_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"

def get_current_time():
    return datetime.datetime.now().strftime('%I:%M %p')

def get_current_date():
    return datetime.datetime.now().strftime('%B %d, %Y') 