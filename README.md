# 🌸 Levos – Your AI Personal Assistant (But With Attitude 😤)

Levos is your Gen-Z-coded AI assistant — powered by **Groq API + LLaMA 3 (8B)** — with a playful personality, emotional memory, a flirty sense of humor, and the ability to *roast* you mid-convo if you act up. It handles tasks like Spotify control, WhatsApp messaging, anime searches, and random internet tools to keep you entertained, informed, and slightly offended.

---

## ✨ Features

* 🎷 **Spotify Control**
  Play songs, skip tracks, control volume, or resume playback with voice commands. Optimized with a smarter polling system — it doesn’t hog resources or spam "🎷 Using \[device]" unnecessarily.
* 📺 **YouTube Playback**
  Search and play YouTube videos using `pywhatkit`.
* 📱 **WhatsApp Messaging**
  Send messages to your saved contacts instantly via WhatsApp. (well only if you have enough patience for it to open whatsapp web on your pc and send it, glitchy sometimes, but works)
* 🌐 **Anime Search**
  Auto-opens anime pages on HiAnime from your voice input.
* 🧠 **Memory with RAG (Retrieval-Augmented Generation)**
  Remembers past conversations using embedding-based search, not full context dumps.
* 🤪 **Roasts, Snarks & Greetings**
  Detects if you're back after hours and greets you like an emotionally unstable ex.
* 💬 **Boredom Busters**
  Built-in tools like:

  * [Bored API](https://www.boredapi.com/)
  * [Advice Slip API](https://api.adviceslip.com/)
  * [Animechan Quote API](https://animechan.xyz/)
  * [DuckDuckGo Search](https://api.duckduckgo.com/)
  * [OpenWeatherMap API](https://openweathermap.org/)
* ❤️ **Conversational AI with Personality**
  Think of Levos as your sarcastic virtual partner: smart, funny, and a little chaotic.
* 💻 **Desktop UI (PyQt5)**
  Slick floating bubble UI with a chat window, mic input, voice button, and animated personality. Styled with a dark Discord-like theme + optional shadow effects.
* 🔊 **Voice Interaction**
  Mic button for real-time speech recognition — say "Spotify play", and boom, music.

---

## 🛠️ Getting Started

### 🔁 Prerequisites

* Python 3.9+
* Groq API Key (for LLaMA 3 chat)
* Spotify Developer Credentials
* Optional: OpenWeatherMap API key

---

### 🩜 Steps to Run

1. **Clone the repo**

   ```bash
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

2. **Create a `.env` file** inside the `Assets` folder and add:

   ```env
   GROQ_API_KEY=your_groq_api_key
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   WEATHER_API_KEY=your_openweathermap_api_key
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Add contacts** in `contacts.json` (sample format included).

5. **Run Levos**

   ```bash
   python run_sakura.py
   ```

---

## Spotify Disclaimer
you also have to finish some setups in the spotify developers page. It's fine if you don't wanna use spotify, else follow the following steps.
1. open the developers portal of spotify and create an account if u don't already have it.
2. Once u have an account go to your dashboard and create an app.
3. Most of the values can be default or u can customize except the "Redirect URIs" Section, make sure u input this URI: http://127.0.0.1:8888/callback
4. Feel free to give a different URI if u want, but remember to change the same in the code too, it's in the "commands.py" file under the core directory.

### refer to this link if u wanna build an app from scratch.
https://developer.spotify.com/documentation/web-playback-sdk/howtos/web-app-player


## 🧠 Memory & Personality

Levos uses **semantic search (RAG)** to recall past messages — more efficient than dumping 20+ chats every time. It's also got a dynamic personality defined in `config/personality.py`, with snarky greetings and roast lines randomly triggered during chat startup.

---

## 📂 File Structure

```
Assets/
├── contacts.json          # WhatsApp contact list
├── .env                   # Your API keys
|-- Conversation_history
|-- Icon.jpg
|-- bg.jpg (optional)
        # Vector-stored memory (for RAG)
config/
core/
llm/
ui/
utils/
run_sakura.py              # Main entry point
```

---

## 🧑‍💻 Made With

* [Groq API](https://groq.com/)
* [LLaMA 3](https://ai.meta.com/llama/)
* [Spotify API](https://developer.spotify.com/)
* [Bored API](https://www.boredapi.com/)
* [Animechan Quotes](https://animechan.xyz/)
* [Advice Slip API](https://api.adviceslip.com/)
* [OpenWeatherMap](https://openweathermap.org/)
* [DuckDuckGo Instant Answer API](https://duckduckgo.com/api)
* [pywhatkit](https://github.com/Ankit404butfound/PyWhatKit)
* [PyQt5](https://riverbankcomputing.com/software/pyqt/)
* [SpeechRecognition](https://pypi.org/project/SpeechRecognition/)

---

## 🤛 Why use Levos?

Because Siri won't flirt back, Alexa doesn't roast you, and ChatGPT is too polite.
Levos is what happens when an LLM is raised on memes, anime, and internet sarcasm.

---
