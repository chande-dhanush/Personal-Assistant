import os
import shutil
import glob
import time

DATA_DIR = os.path.join(os.getcwd(), "data")

PATHS_TO_DELETE = [
    os.path.join(DATA_DIR, "conversation_history.json"),
    os.path.join(DATA_DIR, "memory.db"),
    os.path.join(DATA_DIR, "files.db"),
    os.path.join(DATA_DIR, "vectorstore"),
    os.path.join(DATA_DIR, "user_files"),
    os.path.join(DATA_DIR, "uploads"),
    os.path.join(DATA_DIR, "processed"),
    os.path.join(DATA_DIR, "tmp"),
]

DIRS_TO_RECREATE = [
    os.path.join(DATA_DIR, "vectorstore"),
    os.path.join(DATA_DIR, "user_files"),
    os.path.join(DATA_DIR, "uploads"),
    os.path.join(DATA_DIR, "processed"),
]

def perform_reset():
    print("⚠️ STARTING SYSTEM RESET ⚠️")
    
    # 1. Delete Files/Dirs
    for path in PATHS_TO_DELETE:
        if os.path.exists(path):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    print(f"✅ Deleted file: {path}")
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    print(f"✅ Deleted directory: {path}")
            except Exception as e:
                print(f"❌ Failed to delete {path}: {e}")
        else:
            print(f"ℹ️ Not found (already clean): {path}")

    # 2. Cleanup backups/caches pattern matching
    patterns = [
        os.path.join(DATA_DIR, "*.bak"),
        os.path.join(DATA_DIR, "*_backup*"),
        os.path.join(DATA_DIR, "*.cache"),
    ]
    for pattern in patterns:
        for f in glob.glob(pattern):
            try:
                os.remove(f)
                print(f"✅ Deleted backup/cache: {f}")
            except Exception as e:
                print(f"❌ Failed to delete {f}: {e}")

    # 3. Recreate Directories
    for directory in DIRS_TO_RECREATE:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Recreated directory: {directory}")
        except Exception as e:
            print(f"❌ Failed to recreate {directory}: {e}")

    print("\n✅ System reset completed. All data wiped.")

if __name__ == "__main__":
    perform_reset()
