
import sys
import os

# Add the parent directory of sakura_assistant to sys.path
# This makes 'sakura_assistant' discoverable as a package
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# CRITICAL: Import torch BEFORE PyQt to prevent DLL loading conflict (WinError 1114)
try:
    import torch
except ImportError:
    pass  # torch not available, that's ok

# Check for critical API keys before starting
from dotenv import load_dotenv
load_dotenv()

REQUIRED_KEYS = ["GOOGLE_API_KEY", "GROQ_API_KEY"]
missing_keys = [key for key in REQUIRED_KEYS if not os.getenv(key)]

if missing_keys:
    print("⚠️ Missing API keys detected. Launching Setup Wizard...")
    # Launch setup wizard
    import subprocess
    subprocess.call([sys.executable, "setup_wizard.py"])
    
    # Reload env after wizard closes
    load_dotenv()
    
    # Re-check
    missing_keys = [key for key in REQUIRED_KEYS if not os.getenv(key)]
    if missing_keys:
        print("❌ Critical API keys still missing. Exiting.")
        sys.exit(1)

# Run Memory Maintenance
try:
    from sakura_assistant.utils.maintenance import run_maintenance
    report = run_maintenance()
    if report.get("pruned_memories", 0) > 0:
        print(f"🧹 Maintenance: Pruned {report['pruned_memories']} old memories.")
except Exception as e:
    print(f"⚠️ Maintenance Warning: {e}")

# Now, execute main.py as a module within the sakura_assistant package
from sakura_assistant.main import main

main()
