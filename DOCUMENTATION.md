# Yuki V4 - AI Personal Assistant
## Comprehensive Technical Documentation

---

## 🎯 Overview

**Yuki** is a production-grade personal AI assistant with voice interaction, agentic tool execution, memory persistence, and proactive daily routines. Built with PyQt5, LangChain, and multi-model LLM support.

### Key Features

| Feature | Status | Description |
|---------|--------|-------------|
| **V4 Frozen Pipeline** | ✅ | Router → Planner → Executor → Responder |
| **Multi-LLM Failover** | ✅ | Groq → Gemini cascade with timeout protection |
| **Memory Judger** | ✅ | LLM-based importance filtering for FAISS |
| **Compact Context** | ✅ | Rolling summary + 3 messages + 2 memories |
| **FAISS Vector Store** | ✅ | Memory-mapped with SHA256 integrity |
| **22+ Tools** | ✅ | Gmail, Calendar, Spotify, Notes, Vision, RAG |
| **Kokoro TTS** | ✅ | Neural voice synthesis with idle unload |
| **Proactive Routines** | ✅ | Morning briefings, evening summaries |
| **Thread-Safe Memory** | ✅ | RLock-protected embedding operations |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer                              │
│  ┌─────────────────┐    ┌──────────────────┐                │
│  │   ChatWindow    │    │   NotesPanel     │                │
│  │  (QTextBrowser) │    │   DebugDrawer    │                │
│  └────────┬────────┘    └──────────────────┘                │
│           │ response_ready(dict)                             │
├───────────▼─────────────────────────────────────────────────┤
│                     ViewModel Layer                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              ChatViewModel                               ││
│  │  - QThreadPool for async workers                        ││
│  │  - RLock-protected memory access                        ││
│  └────────┬────────────────────────────────────────────────┘│
├───────────▼─────────────────────────────────────────────────┤
│                      Core Layer (V4)                         │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │   Router   │→│   Planner    │→│   Executor   │→ Responder│
│  │ (Llama 8B) │ │ (Llama 70B)  │ │  (Tool Run)  │           │
│  └────────────┘ └──────────────┘ └──────────────┘           │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │                   Memory Layer                           ││
│  │  FAISS (mmap) + Chroma + Memory Judger + Metadata       ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 V4 LLM Pipeline (FROZEN)

The deterministic 4-step pipeline ensures predictable behavior:

```
═══════════════════════════════════════════════════════════════
FROZEN PIPELINE ARCHITECTURE - DO NOT MODIFY
═══════════════════════════════════════════════════════════════

ROUTER (intent_llm - Llama 8B)
    │
    ├─► SIMPLE → RESPONDER (text-only)
    │
    └─► COMPLEX → PLANNER → EXECUTOR → RESPONDER (text-only)

RULES:
- Router: Classifies SIMPLE/COMPLEX only, no tool calls
- Planner: ONLY model allowed to emit tool JSON
- Executor: Runs tools, outputs plain text
- Responder: Text-only, tool_choice=none, validated output

CONTEXT (single path):
- Rolling summary (if history > 3)
- Last 3 messages
- Top 2 memories
═══════════════════════════════════════════════════════════════
```

### Multi-Model Failover

| Priority | Model | Provider | Timeout | Use Case |
|----------|-------|----------|---------|----------|
| 1 | Llama 3.3 70B | Groq | 60s | Primary - fast, capable |
| 2 | Gemini 2.0 Flash | Google | 60s | Fallback - reliable |

**ReliableLLM Wrapper:**
```python
class ReliableLLM:
    def invoke(self, messages, timeout=60):
        try:
            return invoke_with_timeout(self.primary, messages, timeout)
        except (TimeoutError, Exception):
            return invoke_with_timeout(self.backup, messages, timeout)
```

---

## 🔧 Tools (22+)

### Planner Available Tools

| # | Tool | Arguments | Description |
|---|------|-----------|-------------|
| 1 | `spotify_control` | action, song_name | Play/Pause/Next/Previous music |
| 2 | `play_youtube` | topic | Play video/audio on YouTube |
| 3 | `web_search` | query | Tavily-powered web search |
| 4 | `read_screen` | prompt | Screenshot + Gemini Vision analysis |
| 5 | `gmail_read_email` | query | Read emails with filters |
| 6 | `gmail_send_email` | to, subject, body | Send emails |
| 7 | `calendar_get_events` | date | Fetch calendar events |
| 8 | `calendar_create_event` | title, start_time, end_time | Create events |
| 9 | `tasks_list` | - | List Google Tasks |
| 10 | `tasks_create` | title, notes | Create Google Task |
| 11 | `note_create` | title, content, folder | Create markdown note |
| 12 | `note_append` | title, content, folder | Append to note |
| 13 | `note_read` | title, folder | Read note content |
| 14 | `note_list` | folder | List notes in folder |
| 15 | `file_read` | path | Read local file |
| 16 | `file_write` | path, content | Write local file |
| 17 | `fetch_document_context` | query | RAG document search |
| 18 | `list_uploaded_documents` | - | List ingested docs |
| 19 | `delete_document` | doc_id | Remove document |
| 20 | `list_files` | path | List directory contents |
| 21 | `web_scrape` | url | Scrape and summarize website |
| 22 | `open_app` | app_name | Open desktop application |

### Additional Tools (Not in Planner)

| Tool | Description |
|------|-------------|
| `search_wikipedia` | Wikipedia summary search |
| `search_arxiv` | Scientific paper search |
| `update_user_memory` | Save user preferences |
| `ingest_document` | Add document to RAG |
| `get_rag_telemetry` | System health metrics |
| `clipboard_read/write` | Clipboard operations |

### Note Folder Categories
```
Notes/
├── topics/     # General notes
├── daily/      # Daily logs
├── work/       # Work-related
├── personal/   # Personal notes
└── tech_notes/ # Technical documentation
```

### Security: Path Validation
```python
def _validate_path(path: str):
    # Blocks:
    # - Parent traversal (..)
    # - System directories
    # - Files outside project/notes root
```

---

## 💾 Memory System

### Memory Judger
LLM-based importance classifier that filters what goes into FAISS:

```python
USE_MEMORY_JUDGER = True
MEMORY_JUDGER_MODEL = "llama-3.1-8b-instant"

# Classification outputs:
# ✅ STORE (imp=0.9) - biographical info, important facts
# ⏭️ SKIP (imp=0.5) - acknowledgements, ephemeral commands
```

### V4 Compact Context
```python
ENABLE_V4_SUMMARY = True           # Rolling conversation summary
V4_SUMMARY_INTERVAL = 5            # Update every 5 turns
V4_MAX_RAW_MESSAGES = 3            # Keep last 3 raw messages
V4_MEMORY_LIMIT = 2                # Inject top 2 memories
V4_MEMORY_CHAR_LIMIT = 140         # Max chars per memory
```

### FAISS Configuration
```python
FAISS_MMAP = True                  # Memory-mapped index
LAZY_EMBEDDINGS = True             # Load on first use
EMBEDDING_IDLE_TIMEOUT = 600       # Unload after 10 min

# CRITICAL: RLock for thread-safe embedding operations
self._embed_lock = threading.RLock()  # Prevents deadlock
```

### Data Files
```
data/
├── faiss_index.bin           # Vector embeddings
├── memory_metadata.json      # Message metadata
├── memory_metadata.json.sha256    # Integrity hash
├── conversation_history.json # Full history
└── chroma_store/             # Document RAG
```

---

## 🎤 Voice System

### Text-to-Speech (Kokoro)
- Local neural TTS with natural speech
- Lazy-loaded on first voice request
- Auto-unloads after 5 minutes idle
- 44.1kHz audio via pygame

### Speech Recognition
- Google Speech Recognition API
- Configurable microphone index
- Push-to-talk via UI button

---

## 🗓️ Proactive Routines

### Morning Briefing (8-11 AM)
- Fetches today's calendar events
- Lists pending Google Tasks
- Searches AI/tech news headlines
- Generates personalized greeting

### Evening Summary (11 PM+)
- Previews tomorrow's schedule
- Creates daily log note
- Wishes good rest

---

## 🎭 Personality Engine

### Core Traits
```
- Calm, sharp, introverted
- Quiet confidence
- Affectionate only with the user
- Cool on surface, warm underneath
```

### Behavioral Rules
```
- Keep replies under 3 lines (unless detail requested)
- Never lie, never ramble
- Sarcasm is subtle
- No generic "How can I help you?"
- No emojis unless user uses them
```

---

## ⚡ Performance & Reliability

### Timeout Protection
| Component | Timeout | Fallback |
|-----------|---------|----------|
| LLM calls | 60s | Gemini backup |
| RAG retrieval | 30s | Continue without context |
| API operations | 15s | Socket timeout |

### Thread Safety
```python
# RLock prevents deadlock when unload timer fires
self._embed_lock = threading.RLock()

# History mutations are locked
self._history_lock = threading.Lock()
```

### Worker Lifecycle
```python
# AgentWorker always emits finished signal
finally:
    self.signals.finished.emit(payload)
```

### Lazy Loading
| Resource | Strategy |
|----------|----------|
| LLMs | On first query |
| Embeddings | On first RAG call |
| Spotify client | On first music command |
| Kokoro TTS | On first speech |
| FAISS index | On startup (mmap) |

---

## 📊 Stability Logging

### Health Reports
```json
{
  "errors": 0,
  "warnings": 0,
  "success_calls": 18,
  "flow_events": 74,
  "mem_events": 37,
  "ctx_events": 18
}
```

### Log Functions
```python
log_flow(source, details)    # Flow between components
log_error(message)           # Error tracking
log_warning(message)         # Warning tracking
log_success(details)         # Successful operations
```

---

## 📁 Project Structure

```
Sakura V3/
├── run_sakura.py              # Entry point
├── sakura_assistant/
│   ├── config.py              # Configuration & personality
│   ├── core/
│   │   ├── llm.py             # V4 LLM pipeline
│   │   ├── planner.py         # Tool planning engine
│   │   ├── tools.py           # 22+ tool definitions
│   │   ├── routines.py        # Morning/Evening routines
│   │   ├── scheduler.py       # Background scheduler
│   │   └── reflection.py      # Self-assessment engine
│   ├── ui/
│   │   ├── chat_window.py     # Main UI
│   │   ├── viewmodel.py       # MVVM pattern
│   │   └── workers.py         # Async workers
│   ├── memory/
│   │   ├── faiss_store/       # Vector embeddings (RLock)
│   │   ├── chroma_store/      # Document RAG
│   │   ├── metadata.py        # Document metadata
│   │   └── router.py          # Memory routing
│   └── utils/
│       ├── tts.py             # Kokoro TTS
│       ├── memory_judger.py   # Importance classifier
│       ├── note_tools.py      # Note operations
│       ├── stability_logger.py # Health logging
│       └── summary.py         # Rolling summary
├── Notes/                     # Obsidian-compatible notes
├── data/                      # Persistent data (gitignored)
└── .env                       # API keys (gitignored)
```

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run
python run_sakura.py
```

---

## 📋 Configuration

### .env
```
GOOGLE_API_KEY=your_key
GROQ_API_KEY=your_key
SPOTIFY_CLIENT_ID=your_id
SPOTIFY_CLIENT_SECRET=your_secret
TAVILY_API_KEY=your_key
MICROPHONE_INDEX=1
```

### config.json
```json
{
  "notes_dir": "Notes"
}
```

### Key Config Flags (config.py)
```python
# Memory
FAISS_MMAP = True
MAX_INMEM_HISTORY = 50
USE_MEMORY_JUDGER = True

# V4 Context
ENABLE_V4_SUMMARY = True
V4_MAX_RAW_MESSAGES = 3
V4_MEMORY_LIMIT = 2

# Performance
EMBEDDING_IDLE_TIMEOUT = 600
LAZY_EMBEDDINGS = True
```

---

## 🔄 Signal Contract (V4)

All messages flow through a single signal:

```python
# ViewModel
response_ready = pyqtSignal(dict)

# Payload structure
{
    "role": "user" | "assistant",
    "content": "message text",
    "metadata": {
        "mode": "Chat" | "Complex/Tool" | "Error",
        "tool_used": "spotify_control",
        "latency": "1.23s"
    }
}
```

---

## 🔒 Security

### Path Sandboxing
- Blocks parent traversal (`..`)
- Restricts to project root and notes directory
- Denies access to system files

### API Key Management
All keys stored in `.env` (gitignored):
- Google API, Groq API, Tavily API
- Spotify OAuth credentials
- Google OAuth tokens in `token.json`

---

## 📝 License

Private project - all rights reserved.

---

*Documentation updated for Yuki V4 - December 2025*
