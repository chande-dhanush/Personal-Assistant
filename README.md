# 🌸 Levos – Your Chaotic AI Sidekick (Now Gemini-Powered ⚡)

Levos isn’t your average AI assistant. It’s your emotionally unstable, Gen-Z-coded desktop buddy who flirts, roasts, helps you open Chrome, and reads your screen like a nosy bestie. Now powered by **Gemini 2.5 Flash**, Levos is sassier, smarter, and less crashy than ever.

---

## ✨ What’s New (aka why you should care)
🔁 **Switched from Groq + LLaMA 3 → Gemini 2.5 Flash**  
💡 Supercharged with [LangChain](https://github.com/langchain-ai/langchain) and `langchain-google-genai`  
🧠 **Summarization-based Memory Overhaul** — no more bloated chats, just smart context compression  
🎧 **Wake Word Detection ("Hey Sakura")** — no spying, all offline  
🔧 **Refactored Tools** — fewer errors, more compatibility, still chaotic  
🖼️ **OCR + Screen Reader** — reads what you see, so you can pretend you’re blind and still rule  
🧵 **Qt Thread Fixes** — no more weird crashes when Sakura speaks  
📦 **requirements.txt actually works now**

---

## 🚀 Features
### 🧠 Gemini-Powered Agentic Brain
- Smart summarization kicks in after 20 messages (Gemini handles it).
- Keeps memory lightweight and context-aware.
- Works fine on CPUs (except Gemini API itself).

### 🎤 Wake Word Control
- Uses [Vosk](https://alphacephei.com/vosk/) (offline ASR).
- Just say **“Hey Sakura”** and she pops up, mic-on, glowing and ready.

### 🎧 Spotify Control
- Play/pause/skip songs
- Smarter device handling
- Only roasts your taste if it’s *really* bad

### 📺 YouTube + Web Tools
- Play YouTube videos (via pywhatkit)
- Search Wikipedia, DuckDuckGo, Weather
- OCR reads text from your screen
- Open websites, apps, folders with voice

### 📱 Messaging
- Send WhatsApp messages to saved contacts (glitchy but functional)
- Add new contacts via voice

### 😈 Personality
- Chaotic, flirty, emotionally unstable
- Roasts you if you ghost her for too long
- Sweet enough to make you lower your guard

---

## 💻 Desktop UI (PyQt5)
- Floating chat bubble + animated vibe
- Voice button, mic icon, dark Discord-y theme
- Doesn’t crash anymore (mostly)

---

## 🔧 Setup Guide

### 🔁 Prerequisites
- Python 3.9+
- Gemini API Key (from Google AI Studio)
- Spotify Developer creds *(optional)*
- Whisper ASR/Vosk for speech recognition

### 🔑 Environment Setup
Create `.env` file in the `Assets/` folder with:

```env
GOOGLE_API_KEY=your_gemini_api_key
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
WEATHER_API_KEY=your_openweathermap_api_key
```

### 📦 Install Requirements
```bash
pip install -r requirements.txt
```

### 📂 Folder Structure
```
Assets/
  ├── contacts.json      # WhatsApp contact list
  ├── .env               # Your API keys
  └── Conversation_history/
config/
core/
llm/
ui/
utils/
run_sakura.py            # Launch file
```

### 🏃 Run It
```bash
python run_sakura.py
```

---

## 🧠 Memory & Summarization
- Retains **recent chats**, summarizes older convos using Gemini.
- Based on `faiss-cpu` and `sentence-transformers`.
- Stored under `Assets/Conversation_history/`.

---

## 📜 Supported Commands

### 🎵 Media
- `play the song [name]`  
- `spotify pause/resume/next`  
- `play the video [name]`

### 💬 Info, Fun, System
- `who is [name]` (Wikipedia)
- `joke`, `/time`, `/date`, `system status`
- `/search`, `/weather`, `/mail`

### 💻 Control
- `open [app/folder/website]`
- `screenshot and read screen`
- `launch notepad/chrome/etc.`

### 📱 Messaging
- `send message to [name] saying [msg]`
- `add contact [name, number]`

### 🍿 Anime & Fun
- `/anime`, `I want to watch the anime [name]`
- `/bored`, `/advice`, `/quote`

---

## 🤖 Why Choose Levos?
Because Siri’s boring, Alexa’s basic, and ChatGPT doesn’t flirt back.  
Levos? She's chaotic good, semi-reliable, and dangerously loveable.

---

## 🧠 Built With
- **Google Gemini 2.5 Flash**
- LangChain + AgentExecutor
- Spotify API, YouTube, Wikipedia
- PyTesseract OCR
- PyQt5, pygame
- Vosk ASR, SpeechRecognition
- edge-tts / pyttsx3
- sentence-transformers + faiss-cpu
