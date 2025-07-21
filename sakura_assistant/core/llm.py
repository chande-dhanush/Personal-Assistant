# core/LLM.py

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from ..core.tools import get_all_tools
import os
from ..config import SYSTEM_PERSONALITY
# === 1. Load Gemini API key ===
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "Your API Key")

# === 2. Define Gemini LLM (2.5 Flash) ===
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    streaming=False,
    verbose=True,
    google_api_key=GOOGLE_API_KEY
)

# === 3. Prepare tools ===
all_tools = get_all_tools()

# === 4. Create the agent prompt ===
prompt = ChatPromptTemplate.from_messages([
    ("system", (
        f"{SYSTEM_PERSONALITY}\n"
        "You may use tools to complete tasks. "
        "Only use tools if appropriate, otherwise answer naturally."
    )),
    ("user", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

# === 5. Create and wrap the agent ===
agent = create_tool_calling_agent(llm=llm, tools=all_tools, prompt=prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=all_tools,
    verbose=True,
    handle_parsing_errors=True,
)

# === 6. Function to interact with agent ===
def run_agentic_response(user_input: str, conversation_history=None):
    """Returns Gemini-powered agent's response to user input."""
    try:
        result = agent_executor.invoke({"input": user_input})
        return result.get("output") or "No response."
    except Exception as e:
        return f"⚠️ Agent error: {str(e)}"
