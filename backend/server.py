from flask import Flask, request, jsonify
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sakura_assistant.config import get_config
from sakura_assistant.core.llm import run_agentic_response

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "system": "Sakura Assistant"})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message')
    history = data.get('history', [])
    
    if not user_input:
        return jsonify({"error": "No message provided"}), 400
        
    response = run_agentic_response(user_input, history)
    return jsonify({"response": response})

@app.route('/execute_tool', methods=['POST'])
def execute_tool_endpoint():
    # Placeholder for direct tool execution via API
    return jsonify({"status": "not_implemented"})

if __name__ == '__main__':
    port = 5050
    print(f"🚀 Sakura Backend running on port {port}")
    app.run(host='0.0.0.0', port=port)
