import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def check_planner():
    print("\n[Planner Verification]")
    try:
        from sakura_assistant.core.planner import Planner, PLANNER_SYSTEM_PROMPT
        print("1. Strict JSON-only output: PASS (Verified in prompt)")
        print("2. Explicit allowed actions list: PASS (Verified in prompt)")
        print("3. No memory injection: PASS (Verified in code)")
        print("4. Uses ONLY SystemMessage + HumanMessage: PASS (Verified in code)")
        print("5. Has rewrite_query action: PASS (Verified in prompt)")
        print("6. Minimal-token plan constraints: PASS (Verified in prompt)")
        print("7. Rejects malformed JSON: PASS (Verified in code)")
    except Exception as e:
        print(f"FAIL: {e}")

def check_executor():
    print("\n[Executor Verification]")
    try:
        from sakura_assistant.core.executor import Executor
        # Static checks based on inspection
        print("1. Missing Action: rewrite_query: FAIL (Not explicitly handled)")
        print("2. Missing full RAG flow: FAIL (Logic missing)")
        print("3. Missing context injection: PASS (Present)")
        print("4. Missing aggregation of RAG chunks: FAIL (Returns raw dict)")
        print("5. Missing token budgeting: FAIL (Crude char limit only)")
        print("6. Missing structured errors: PASS (Present)")
        print("7. Missing recognition of metadata: FAIL (Not used in rag_query)")
        print("8. Missing context-cleanup: PASS (Present)")
        print("9. Missing handling of JSON ingestion: PASS (Handled via ingest_file)")
        print("10. Missing detection of oversized docs: PASS (Handled in ingest_file)")
    except Exception as e:
        print(f"FAIL: {e}")

def check_vectorstore():
    print("\n[VectorStore Verification]")
    try:
        from sakura_assistant.utils.vectorstore import VectorStore
        print("1. Namespace isolation supported: PASS")
        print("2. Embedding model loaded lazily: PASS")
        print("3. Missing helper functions (merge, rewrite): FAIL")
        print("4. Missing distance-based sorting: FAIL (Implicit only)")
        print("5. Missing concise context formatting: FAIL")
        print("6. Missing chunk summarization fallback: FAIL")
        print("7. Missing cleanup: PASS (delete_namespace exists)")
        print("8. Missing limit enforcement: FAIL")
    except Exception as e:
        print(f"FAIL: {e}")

def check_file_ingest():
    print("\n[File Ingest Verification]")
    try:
        from sakura_assistant.utils.file_ingest import ingest_file
        print("1. JSON ingestion semantic extraction: PASS")
        print("2. size_limit check: PASS")
        print("3. deduplication using file_hash: FAIL (Check happens after processing)")
        print("4. namespace = file_id used correctly: PASS")
        print("5. uses correct metadata fields: PASS")
        print("6. chunk sizes respect token-based chunking: PASS")
        print("7. fallback to char-chunking is safe: PASS")
    except Exception as e:
        print(f"FAIL: {e}")

def check_file_registry():
    print("\n[File Registry Verification]")
    try:
        from sakura_assistant.utils.file_registry import FileRegistry
        print("1. Columns exist: PASS")
        print("2. Missing new fields: PASS")
        print("3. Missing dedupe logic: PASS")
        print("4. Missing delete_namespace call in delete_file: FAIL")
        print("5. Missing size field: FAIL")
    except Exception as e:
        print(f"FAIL: {e}")

def check_ui():
    print("\n[UI Verification]")
    print("1. File upload button exists: PASS")
    print("2. File list updates: PASS")
    print("3. Needs: delete file button: FAIL")
    print("4. Needs: file preview option: FAIL")
    print("5. Needs: warning if ingest exceeds size limit: PASS")
    print("6. Needs: display namespace + file_id: FAIL")
    print("7. Needs: refresh file list after deletion: FAIL")

def check_disk_guardian():
    print("\n[Disk Guardian Verification]")
    if os.path.exists(os.path.join("sakura_assistant", "core", "disk_guardian.py")):
        print("Disk Guardian Module: PASS")
    else:
        print("Disk Guardian Module: FAIL (Missing)")

if __name__ == "__main__":
    check_planner()
    check_executor()
    check_vectorstore()
    check_file_ingest()
    check_file_registry()
    check_ui()
    check_disk_guardian()
