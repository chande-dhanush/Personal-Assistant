
# 🌸 Levos – Your AI Personal Assistant

Levos is a voice/chat-based AI assistant built using the **Groq API** and powered by **LLaMA 3 (8B)**. It's not just smart — it’s *personal*, with memory, personality, and the ability to handle your daily tasks and chat like your ideal virtual companion 💬🎵📱💻.

---

## ✨ Features

- 🎧 **Spotify Control**: Play songs, skip tracks, and manage playback using voice commands.
- 📺 **YouTube Playback**: Search and play YouTube videos (basic playback only).
- 💬 **WhatsApp Messaging**: Send WhatsApp messages to your saved contacts.
- 🌐 **Anime Search**: Quickly search anime info using your voice.
- ❤️ **Conversational AI**: Personalized conversation with memory, emotions, and a vibe like your virtual girlfriend 😄.

---

## 🛠️ Getting Started

### 🔁 Prerequisites

- Python 3.9+
- Groq API Key (for LLaMA3 chat)
- Spotify Developer API credentials
- Optional: Selenium for WhatsApp automation

---

### 🪜 Steps to Run

1. **Clone this repository**
   ```bash
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

2. **Create a `.env` file** inside the `Assets` folder and add:
   ```env
   GROQ_API_KEY=your_groq_api_key
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIFY_REDIRECT_URI=your_spotify_redirect_uri
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add contacts** in `contacts.json` for WhatsApp messaging (sample format is already included).

5. **Run the assistant**
   ```bash
   python run_sakura.py
   ```

---

## 🧠 Memory & Personality

Levos remembers your preferences, interests, and past interactions to make conversations feel real and engaging. You can modify this memory in the `levos_memory.json` file.

---

## 📂 File Structure

```
Assets/
├── contacts.json          # WhatsApp contact list
├── .env                   # Your API keys
levos_memory.json          # Assistant's memory about you
run_sakura.py              # Main script to launch assistant
config/
core/
llm/
```

---
## 🧑‍💻 Made With

- [Groq API](https://groq.com/)
- [Spotify API](https://developer.spotify.com/)
- pywhatkit for whatsapp and Youtube
- [Open Source ❤️]

---
