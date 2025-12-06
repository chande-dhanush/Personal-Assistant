import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from sakura_assistant.core.llm import run_agentic_response
from sakura_assistant.utils.file_ingest import ingest_file
from sakura_assistant.utils.file_registry import get_file_registry
from sakura_assistant.utils.vectorstore import get_vectorstore

def test_single_step():
    print("\n--- Test 1: Single Step ---")
    response = run_agentic_response("Hi there!", [])
    print(f"Response: {response}")

def test_file_ingest_and_rag():
    print("\n--- Test 2: File Ingest & RAG ---")
    # Create a dummy file
    dummy_path = "test_doc.txt"
    with open(dummy_path, "w", encoding="utf-8") as f:
        f.write("Sakura is an advanced AI assistant developed by a brilliant engineer. It uses a multi-step planner and executor architecture.")
    
    print(f"Ingesting {dummy_path}...")
    result = ingest_file(dummy_path)
    print(result)
    
    # Verify Registry
    registry = get_file_registry()
    files = registry.list_files()
    print(f"Registry Files: {len(files)}")
    
    # Verify Vector Store
    vs = get_vectorstore()
    query_res = vs.query("Sakura architecture", namespace=files[-1]['file_id'])
    print(f"Vector Query Result: {len(query_res['chunks'])} chunks found.")
    
    print("Querying Agent (RAG)...")
    response = run_agentic_response("What is Sakura's architecture based on the uploaded document?", [])
    print(f"Response: {response}")
    
    # Clean up
    if os.path.exists(dummy_path):
        os.remove(dummy_path)

def test_recursive_logic():
    print("\n--- Test 3: Recursive Logic (Generate + Write) ---")
    response = run_agentic_response("Write a short poem about cherry blossoms and save it to 'data/user_files/poem.txt'.", [])
    print(f"Response: {response}")
    
    # Verify file
    poem_path = os.path.join("data", "user_files", "poem.txt")
    if os.path.exists(poem_path):
        print(f"✅ File created at {poem_path}")
        with open(poem_path, "r", encoding="utf-8") as f:
            print(f"Content:\n{f.read()}")
    else:
        print("❌ File not created.")

def test_json_ingest():
    print("\n--- Test 4: JSON Ingestion ---")
    json_path = "test_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write('{"name": "Sakura", "version": "2.0", "features": ["RAG", "Planning"]}')
        
    result = ingest_file(json_path)
    print(f"JSON Ingest Result: {result}")
    
    if os.path.exists(json_path):
        os.remove(json_path)

if __name__ == "__main__":
    # Ensure API keys are loaded
    from dotenv import load_dotenv
    load_dotenv()
    
    test_single_step()
    test_file_ingest_and_rag()
    test_recursive_logic()
    test_json_ingest()
