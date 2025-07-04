from groq import Groq
from ..config import GROQ_API_KEY, SYSTEM_PERSONALITY

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

def sakura_llm_response(user_message, history=None):
    messages = [{"role": "system", "content": SYSTEM_PERSONALITY}]
    if history:
        # Only keep the last 3 exchanges for brevity
        for msg in history[-15:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="compound-beta-mini",
    )
    return chat_completion.choices[0].message.content 
