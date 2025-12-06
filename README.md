# 🌸 Sakura Assistant

> **A Voice-Activated, Agentic AI Desktop Companion**

Sakura is a powerful, modular desktop assistant built with **Python**, **PyQt5**, and **LangGraph**. She lives as a floating bubble on your desktop, ready to help you control your PC, play music, search the web, and remember your conversations.

## ✨ Key Features

- **🗣️ Voice Interaction**: Natural conversations using **Google Speech Recognition** (Inputs) and **Edge-TTS** (Outputs).
- **🧠 Agentic Intelligence**: Powered by **Gemini 2.5 Flash** (Reasoning) and **Llama 3.3** (Fallback).
- **💾 Incremental Memory**:
  - **Vector Memory (FAISS)**: Remembers context from previous conversations.
  - **User Facts**: Automatically learns your likes/dislikes (e.g., "I love sushi") and updates its long-term profile.
  - **Document RAG**: Upload PDFs or text files to chat with them.
- **🎵 Media Control**:
  - **Spotify**: Play, pause, skip tracks seamlessly.
  - **YouTube**: Auto-fallback for video/music search.
- **👁️ Vision**: Reads text on your screen using **Tesseract OCR**.
- **🖥️ Desktop Control**: Launch apps, read clipboards, and manage tasks.
- **⚙️ Setup Wizard**: Easy GUI for configuring API keys.

## 🚀 Installation

### Prerequisites
- Windows 10/11
- Python 3.10+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (Install & add to PATH)

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/sakura-assistant.git
cd sakura-assistant

# Create virtual environment (Recommended)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run
```bash
python run_sakura.py
```
*On the first run, a Setup Wizard will appear asking for your API Keys.*

## 🛠️ Configuration

Required Keys (Free Tiers Available):
- **GOOGLE_API_KEY**: For Gemini Brain.
- **GROQ_API_KEY**: For Llama Backup.
- **SPOTIFY_CLIENT_ID/SECRET**: (Optional) For music control.

## 🧩 Architecture

Sakura uses a **Hybrid Agentic RAG** architecture:
1.  **Input**: Voice/Text/Vision.
2.  **Memory**: Retrieves User Profile (JSON) + Context (FAISS) + Docs (ChromaDB).
3.  **Reasoning**: LangGraph Agent decides which tool to use.
4.  **Tools**: Spotify, Gmail, Calendar, Web Search (Tavily), System Ops.
5.  **Output**: Synthesized Voice + UI Response.

## 🤝 Contributing
Open to PRs! Please check `PROJECT_BIBLE.md` (if available) for architecture details.

## 📄 License
MIT License



## For more information on the entire implementation of the project, refer to Implementation Summary.mb
