
# 🌸 Levos – Your AI Personal Assistant (But With Attitude 😤)

Levos is your Gen-Z-coded AI assistant — powered by **Groq API + LLaMA 3 (8B)** — with a playful personality, emotional memory, a flirty sense of humor, and the ability to *roast* you mid-convo if you act up. It handles tasks like Spotify control, WhatsApp messaging, anime searches, and random internet tools to keep you entertained, informed, and slightly offended.

---

## ✨ Features

* 🎧 **Spotify Control**
  Play songs, skip tracks, control volume, or resume playback with voice commands.
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

---

## 🛠️ Getting Started

### 🔁 Prerequisites

* Python 3.9+
* Groq API Key (for LLaMA 3 chat)
* Spotify Developer Credentials
* Optional: OpenWeatherMap API key

---

### 🪜 Steps to Run

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
   SPOTIFY_REDIRECT_URI=your_spotify_redirect_uri
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
|-= bg.jpg (optional)
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

---

## 🙋‍♂️ Why use Levos?

Because Siri won't flirt back, Alexa doesn't roast you, and ChatGPT is too polite.
Levos is what happens when an LLM is raised on memes, anime, and internet sarcasm.

---

