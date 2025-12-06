import sys
import os
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from sakura_assistant.core.executor import Executor
from sakura_assistant.core.llm import run_agentic_response

def test_path_correction():
    print("\n--- Test: Path Correction ---")
    
    # Mock LLM (not needed for this specific test if we call _route_step directly, but let's use Executor)
    class MockLLM:
        def invoke(self, *args, **kwargs):
            return "Mock response"
            
    executor = Executor(MockLLM())
    
    # Test 1: Write with filename only
    print("1. Write 'test_note.txt' (Should auto-correct to data/user_files/)")
    res = executor._route_step("write_file", {"path": "test_note.txt", "content": "Test content"})
    print(f"Result: {res}")
    
    expected_path = os.path.join(os.getcwd(), "data", "user_files", "test_note.txt")
    if os.path.exists(expected_path):
        print("✅ File created in correct location.")
        os.remove(expected_path)
    else:
        print(f"❌ File NOT found at {expected_path}")

    # Test 2: Read with filename only
    # Create file first
    with open(expected_path, "w") as f:
        f.write("Read me")
        
    print("\n2. Read 'test_note.txt' (Should auto-correct)")
    res = executor._route_step("read_file", {"path": "test_note.txt"})
    print(f"Result: {res}")
    
    if "Read me" in str(res):
        print("✅ Read successful.")
    else:
        print("❌ Read failed.")
        
    if os.path.exists(expected_path):
        os.remove(expected_path)

if __name__ == "__main__":
    test_path_correction()
