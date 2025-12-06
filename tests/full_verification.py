import sys
import os
import time
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from sakura_assistant.core.llm import run_agentic_response
from sakura_assistant.utils.file_ingest import ingest_file
from sakura_assistant.utils.file_registry import get_file_registry
from sakura_assistant.utils.vectorstore import get_vectorstore
from sakura_assistant.core.disk_guardian import get_disk_guardian

def test_full_rag_flow():
    print("\n--- Test 1: Full RAG Flow (Ingest -> Rewrite -> Query -> Generate) ---")
    # 1. Ingest
    dummy_path = "rag_test.txt"
    with open(dummy_path, "w", encoding="utf-8") as f:
        f.write("Sakura's new architecture includes a Disk Guardian module that auto-prunes old files when disk usage exceeds 90%.")
    
    print(f"Ingesting {dummy_path}...")
    ingest_file(dummy_path)
    
    # 2. Query (Agent should use RAG)
    print("Querying Agent...")
    response = run_agentic_response("What does the Disk Guardian do in Sakura's architecture?", [])
    print(f"Response: {response}")
    
    # Cleanup
    if os.path.exists(dummy_path):
        os.remove(dummy_path)

def test_json_ingest():
    print("\n--- Test 2: JSON Ingestion ---")
    json_path = "config_test.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write('{"module": "DiskGuardian", "threshold": 0.9, "action": "prune"}')
        
    res = ingest_file(json_path)
    print(f"Ingest Result: {res}")
    
    # Verify retrieval
    response = run_agentic_response("What is the threshold for DiskGuardian based on the config file?", [])
    print(f"Response: {response}")
    
    if os.path.exists(json_path):
        os.remove(json_path)

def test_deduplication():
    print("\n--- Test 3: Deduplication ---")
    dup_path = "dup_test.txt"
    with open(dup_path, "w", encoding="utf-8") as f:
        f.write("This is a duplicate file test.")
        
    print("Ingest 1:")
    res1 = ingest_file(dup_path)
    print(res1)
    
    print("Ingest 2 (Should fail/warn):")
    res2 = ingest_file(dup_path)
    print(res2)
    
    if os.path.exists(dup_path):
        os.remove(dup_path)

def test_disk_guardian():
    print("\n--- Test 4: Disk Guardian ---")
    dg = get_disk_guardian()
    stats = dg.get_disk_usage()
    print(f"Disk Stats: {stats}")
    
    msg = dg.check_and_prune()
    print(f"Prune Check: {msg}")

def test_registry_deletion():
    print("\n--- Test 5: Registry Deletion ---")
    # Create temp file
    temp_path = "del_test.txt"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write("Delete me.")
    res = ingest_file(temp_path)
    file_id = res.get("file_id")
    
    if not file_id:
        print("Failed to ingest temp file.")
        return

    print(f"Ingested ID: {file_id}")
    
    registry = get_file_registry()
    registry.delete_file(file_id)
    print("Deleted file.")
    
    # Verify gone
    files = registry.list_files()
    found = any(f['file_id'] == file_id for f in files)
    print(f"File exists in registry? {found}")
    
    if os.path.exists(temp_path):
        os.remove(temp_path)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    test_full_rag_flow()
    test_json_ingest()
    test_deduplication()
    test_disk_guardian()
    test_registry_deletion()
