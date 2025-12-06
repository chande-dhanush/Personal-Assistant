import os
import json
import re
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from .tools import get_all_tools

# Executor System Prompt
EXECUTOR_SYSTEM_PROMPT = """You are the execution engine. Use the provided plan and shared context to perform each step. Only act according to declared actions. After all steps, output the final user-facing message."""

SAFE_WRITE_DIR = os.path.join(os.getcwd(), "data", "user_files")

class Executor:
    def __init__(self, llm):
        self.llm = llm
        self.tools = {t.name: t for t in get_all_tools()}
        self.shared_context = {}
        os.makedirs(SAFE_WRITE_DIR, exist_ok=True)

    def execute(self, plan: List[Dict[str, Any]]) -> str:
        """
        Executes a list of steps sequentially.
        """
        self.shared_context = {} # Reset context for new execution
        final_response = "✅ Execution completed."

        print(f"🚀 Starting Execution of {len(plan)} steps...")

        try:
            for step in plan:
                step_id = step.get("id")
                action = step.get("action")
                params = step.get("params", {})
                description = step.get("description", "")

                print(f"▶️ Step {step_id}: {action} - {description}")

                # Substitute variables in params
                resolved_params = self._resolve_params(params)

                result = self._route_step(action, resolved_params)
                self.shared_context[f"step_{step_id}_result"] = result
                
                # If this is the final reply, capture it
                if action == "reply_user":
                    final_response = result

        except Exception as e:
            error_msg = f"❌ Execution failed at step {step_id}: {e}"
            print(error_msg)
            return error_msg
        finally:
            # Cleanup transient plan data
            self.shared_context = {} 

        return final_response

    def _resolve_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replaces $step_N_result variables with actual values from shared_context.
        """
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str):
                # Check for $step_N_result pattern
                match = re.search(r"\$step_(\d+)_result", v)
                if match:
                    key = match.group(0).replace("$", "") # step_N_result
                    if key in self.shared_context:
                        val = self.shared_context[key]
                        if v == match.group(0):
                            resolved[k] = val
                        else:
                            resolved[k] = v.replace(match.group(0), str(val))
                    else:
                        resolved[k] = v # Variable not found, keep as is
                else:
                    resolved[k] = v
            else:
                resolved[k] = v
        return resolved

    def _route_step(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Routes the action to the appropriate tool or logic.
        """
        try:
            if action == "inform_user":
                return f"ℹ️ {params.get('message')}"
            
            elif action == "reply_user":
                return params.get("message")

            elif action == "search_web":
                if "web_search" in self.tools:
                    return self.tools["web_search"].invoke({"query": params.get("query")})
                return {"error": True, "reason": "Web search tool not available."}

            elif action == "rewrite_query":
                query = params.get("query")
                # Simple rewrite using LLM
                messages = [
                    SystemMessage(content="Rewrite this query to be more specific and optimized for vector search retrieval."),
                    HumanMessage(content=query)
                ]
                response = self.llm.invoke(messages)
                return response.content

            elif action == "rag_query":
                # RAG is currently disabled as vectorstore was removed for consistency.
                return {"error": True, "reason": "RAG system is currently disabled for maintenance."}

            elif action == "check_ingest_state":
                from ..core.ingest_state import get_ingesting
                return get_ingesting()

            elif action == "read_file":
                path = params.get("path")
                # Auto-correct path if just a filename
                if not os.path.isabs(path) and not path.startswith("data/"):
                     path = os.path.join(SAFE_WRITE_DIR, path)
                
                if "file_read" in self.tools:
                    return self.tools["file_read"].invoke({"path": path})
                return {"error": True, "reason": "File read tool not available."}

            elif action == "write_file":
                path = params.get("path")
                content = params.get("content")
                
                # Auto-correct path if just a filename
                if not os.path.isabs(path) and not path.startswith("data/"):
                     path = os.path.join(SAFE_WRITE_DIR, path)
                
                # Protected Mode Validation
                if not self._is_safe_path(path):
                    return {"error": True, "reason": f"Security Error: Writing to '{path}' is not allowed. Use 'data/user_files/'."}
                    
                if "file_write" in self.tools:
                    return self.tools["file_write"].invoke({"path": path, "content": content})
                return {"error": True, "reason": "File write tool not available."}
                
            elif action == "append_file":
                 path = params.get("path")
                 content = params.get("content")
                 
                 # Auto-correct path if just a filename
                 if not os.path.isabs(path) and not path.startswith("data/"):
                     path = os.path.join(SAFE_WRITE_DIR, path)
                 
                 if not self._is_safe_path(path):
                    return {"error": True, "reason": f"Security Error: Appending to '{path}' is not allowed."}

                 try:
                     with open(path, "a", encoding="utf-8") as f:
                         f.write(content)
                     return f"✅ Appended to {path}"
                 except Exception as e:
                     return {"error": True, "reason": f"Append failed: {e}"}

            elif action == "generate_content":
                prompt = params.get("prompt")
                context_input = params.get("context", "")
                context_str = str(context_input)

                # Token Budget: Truncate context if still too long
                if len(context_str) > 8000: # Approx 2000 tokens
                    context_str = context_str[:8000] + "... [TRUNCATED]"
                
                messages = [
                    SystemMessage(content="You are a helpful assistant. Generate content based on the user request and context."),
                    HumanMessage(content=f"Context:\n{context_str}\n\nTask: {prompt}")
                ]
                response = self.llm.invoke(messages)
                return response.content

            elif action == "summarize":
                text = params.get("text")
                # Token Budget: Truncate text if too long
                if len(text) > 12000: # Approx 3000 tokens
                    text = text[:12000] + "... [TRUNCATED]"
                    
                messages = [
                    SystemMessage(content="Summarize the following text concisely."),
                    HumanMessage(content=text)
                ]
                response = self.llm.invoke(messages)
                return response.content

            elif action == "embed_document":
                 from ..memory.ingestion.pipeline import get_ingestion_pipeline
                 pipeline = get_ingestion_pipeline()
                 return pipeline.ingest_file_sync(params.get("path"))

            elif action == "store_memory":
                 from ..memory.faiss_store import add_message_to_memory
                 add_message_to_memory(params.get("content"), "user")
                 return "✅ Memory stored."
            
            elif action == "disk_maintenance":
                from .disk_guardian import get_disk_guardian
                dg = get_disk_guardian()
                return dg.check_and_prune()

            else:
                return {"error": True, "reason": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"error": True, "reason": str(e)}

    def _is_safe_path(self, path: str) -> bool:
        """Ensure path is within SAFE_WRITE_DIR."""
        # Normalize paths
        abs_path = os.path.abspath(path)
        abs_safe = os.path.abspath(SAFE_WRITE_DIR)
        return abs_path.startswith(abs_safe)
