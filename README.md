<![CDATA[# AI Support Bot — Nico Market

[![Russian](https://img.shields.io/badge/🇷🇺_Русский-blue.svg)](README_RU.md)
[![English](https://img.shields.io/badge/🇬🇧_English-red.svg)](README.md)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![aiogram 3.x](https://img.shields.io/badge/aiogram-3.x-009688.svg)](https://docs.aiogram.dev/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-black.svg)](https://ollama.ai/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)

A production-ready AI support assistant for Telegram built on a **RAG (Retrieval-Augmented Generation)** architecture. Runs fully locally via **Ollama** — no cloud APIs, no recurring costs, complete data privacy.

> **TL;DR:** A Telegram bot that answers customer questions about a store using a local LLM + vector search over a knowledge base, with streaming responses, anti-hallucination guardrails, a built-in Mini App storefront, and a one-click orchestrator that manages the bot, web server, and SSH tunnel automatically.

---

## ✨ Key Features

### 🧠 RAG Pipeline
- **Semantic search** via `SentenceTransformers` (`paraphrase-multilingual-MiniLM-L12-v2`) + `ChromaDB` with cosine distance and normalized embeddings.
- **Chunking** via `langchain-text-splitters` with `RecursiveCharacterTextSplitter` (800 chars, 150 overlap) and smart separators (`===`, `---`, `\n\n`, etc.) to respect document structure.
- **Context-aware search**: the bot analyzes conversation history for multi-turn follow-up questions, so the user doesn't have to repeat themselves.
- **Distance-based filtering**: chunks with cosine distance > 0.9 are silently discarded, preventing low-relevance noise from reaching the LLM.

### 🛡️ Anti-Hallucination System (Multi-Layer)
1. **System prompt**: 6 strict rules baked into the LLM prompt — grounding in context only, no fake products/URLs/contacts, natural tone, Russian-only responses, category-level answers for broad questions.
2. **Programmatic guardrails** (`rag/guardrails.py`): regex-based post-processing that validates every response before delivery:
   - Detects hallucinated phone numbers, emails, and URLs that don't match a whitelist.
   - Catches prompt leakage markers ("according to the instructions", "in my database").
   - If ≥ 3 warnings fire simultaneously, the entire response is replaced with a safe fallback redirecting the user to a human manager.
3. **Graceful fallback**: if zero chunks pass the distance threshold, the bot skips the LLM entirely and returns a curated fallback answer with real support contacts.

### ⚡ Streaming Responses
- The bot uses Ollama's **streaming Chat API** — tokens appear in real-time inside the Telegram message.
- Throttled message edits (every 1.5s) to stay within Telegram API rate limits, with silent error recovery on flood errors.
- A semaphore (`MAX_CONCURRENT_GENERATIONS = 1`) serializes generation requests to prevent resource contention on limited hardware.

### 🛒 Telegram Mini App (WebApp)
- A fully responsive storefront embedded as a **Telegram Mini App** (WebApp).
- Live product search, category tabs (Hardware, Software, Services), product detail modals with glassmorphism design.
- Interactive shopping cart with quantity controls, real-time totals, and order checkout that sends structured data back to the bot.
- User avatar and name are passed via URL params and displayed in the header.
- Product catalog loaded from a local `products.json` (22K+ entries).

### 🔄 Orchestrator (`run_all.py`)
A single-script supervisor that manages the entire stack:
1. **Kills orphaned processes** — cleans up stale bot instances and SSH tunnels from previous runs (Windows-specific via `Get-CimInstance`).
2. **Starts an HTTP server** (port 8000) serving the WebApp from `webapp/`.
3. **Establishes an SSH tunnel** to `localhost.run` with keep-alive (15s interval, 3 max misses).
4. **Auto-updates `.env`** with the new tunnel URL so the bot always has the correct `WEBAPP_URL`.
5. **Monitors both processes** in a loop:
   - Auto-restarts the bot if it crashes.
   - **Active tunnel health checking**: pings the tunnel URL and detects stale tunnels ("no tunnel here" pages, HTTP 502/503/504) — even if the SSH process itself is still alive.
   - Reconnects with exponential backoff (up to 5 retries, max 30s delay).
6. **Graceful shutdown** on `Ctrl+C` — terminates all child processes with timeouts.

### 🏗️ Production Hardening
- **Global `ErrorHandlingMiddleware`**: catches any unhandled exception in any handler and sends a polite apology to the user.
- **Background memory cleanup**: a coroutine runs every 5 minutes, purging expired sessions (TTL: 10 min) and stale rate-limit records (>1 hour old).
- **Rate limiting**: 3-second cooldown per user, enforced via the memory module.
- **Message length validation**: rejects messages over 1000 chars.
- **Windows `wakeup_loop`**: a 0.5s async sleep loop that keeps the event loop responsive to `Ctrl+C` on Windows (a known `asyncio` quirk).
- **Singleton `aiohttp` session** with `asyncio.Lock` to prevent race conditions during concurrent access.
- **Graceful shutdown sequence**: cancels background tasks → waits with timeout → closes aiohttp session → closes bot session.

---

## 📁 Project Structure

```
ai-support-bot/
├── main.py                  # Entrypoint: bot init, polling, background tasks
├── config.py                # Env variables, paths, memory/Ollama settings
├── run_all.py               # Full-stack orchestrator (bot + server + tunnel)
├── run_all.bat              # Windows launcher for run_all.py
├── run_bot.bat              # Windows launcher for bot-only mode
├── bot/
│   ├── handlers.py          # /start, /help, /new, callbacks, WebApp data, message handling
│   ├── memory.py            # ConversationMemory: sessions, TTL, rate limiting, cleanup
│   └── middleware.py        # ErrorHandlingMiddleware
├── rag/
│   ├── loader.py            # Document loader + RecursiveCharacterTextSplitter
│   ├── retriever.py         # ChromaDB indexing + semantic search with distance filtering
│   ├── chain.py             # Ollama streaming generation, system prompt, session management
│   └── guardrails.py        # Regex-based hallucination detection & response validation
├── data/
│   ├── knowledge_base/      # Source .txt files (about, contacts, catalog, policies, FAQ, etc.)
│   ├── chroma_db/           # Persistent ChromaDB vector storage (auto-generated)
│   ├── prompts/             # System prompt (system.txt)
│   └── memory.db            # SQLite memory store
├── webapp/
│   ├── index.html           # Mini App frontend
│   ├── style.css            # Glassmorphism UI styles
│   ├── app.js               # Product catalog, cart logic, Telegram WebApp API integration
│   ├── products.json        # Product database
│   └── avatars/             # User avatar assets
├── tests/
│   └── test_guardrails.py   # Unit tests for guardrails validation
├── Dockerfile               # Python 3.10-slim based image
├── docker-compose.yml       # Single-service config with host networking for Ollama access
├── requirements.txt         # Python dependencies
├── .env.example             # Template for environment variables
└── .gitignore
```

---

## 🛠 Technology Stack

| Layer | Technology |
|-------|-----------|
| **Bot Framework** | `aiogram 3.x` (Python 3.10+) |
| **LLM Engine** | `Ollama` (default model: `qwen2.5-coder:32b`) |
| **Embeddings** | `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`) |
| **Vector Database** | `ChromaDB` (persistent, cosine distance) |
| **Text Splitting** | `langchain-text-splitters` (`RecursiveCharacterTextSplitter`) |
| **HTTP Client** | `aiohttp` (singleton session pattern) |
| **WebApp** | Vanilla HTML/CSS/JS + Telegram WebApp API |
| **Tunnel** | SSH to `localhost.run` (auto-managed) |
| **Containerization** | Docker + Docker Compose |

---

## 📦 Quick Start

### Prerequisites
- **Python 3.10+** (for local development)
- **[Ollama](https://ollama.ai/)** installed and running
- **Docker & Docker Compose** (for containerized deployment)
- **SSH client** (for the tunnel in `run_all.py` mode)

### Option 1: Local Development (Windows)

```bash
# 1. Clone the repo
git clone https://github.com/your-username/ai-support-bot.git
cd ai-support-bot

# 2. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env — set BOT_TOKEN from @BotFather
```

**Run bot only** (no WebApp, no tunnel):
```bash
python main.py
# or
run_bot.bat
```

**Run full stack** (bot + WebApp server + SSH tunnel):
```bash
python run_all.py
# or
run_all.bat
```

### Option 2: Docker

```bash
# 1. Configure .env
copy .env.example .env
# Edit .env — set BOT_TOKEN, adjust OLLAMA_BASE_URL if needed

# 2. Add knowledge base files
# Place .txt files into data/knowledge_base/

# 3. Launch
docker-compose up --build -d
```

> **Note:** The Docker container uses `network_mode: "host"` so the bot can reach Ollama running on localhost. If Ollama is on a different host, update `OLLAMA_BASE_URL` in `.env`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | — (required) | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5-coder:32b` | LLM model name |
| `WEBAPP_URL` | `https://nico-market-catalog.loca.lt` | WebApp public URL (auto-updated by `run_all.py`) |

---

## 📝 Knowledge Base

The bot's knowledge comes from plain `.txt` files in `data/knowledge_base/`. On startup, they are:
1. Loaded and split into chunks (800 chars, 150 overlap).
2. Embedded using `paraphrase-multilingual-MiniLM-L12-v2`.
3. Stored in ChromaDB with source metadata.

Current knowledge base structure:
| File | Content |
|------|---------|
| `01_about.txt` | Company info and history |
| `02_contacts.txt` | Official contacts and working hours |
| `03_catalog.txt` | Full product catalog with prices |
| `04_policies.txt` | Return, delivery, and warranty policies |
| `05_subscriptions.txt` | Subscription plans |
| `06_faq.txt` | Frequently asked questions |
| `07_team.txt` | Team members |
| `08_bot_persona.txt` | Bot personality and behavior rules |

To update: edit/add `.txt` files and restart the bot — the index rebuilds automatically.

---

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

Currently covers guardrails validation (hallucinated phones, emails, URLs, prompt leaks).

---

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message + main menu + WebApp button |
| `/help` | Usage guide |
| `/new` | Reset conversation context |

Inline buttons: **Order status**, **Return policy**, **Contact manager**.

---

## ⚙️ Configuration Constants

| Constant | Value | Location |
|----------|-------|----------|
| `MEMORY_MAX_MESSAGES` | 4 | `config.py` — max messages per session |
| `MEMORY_SESSION_TTL` | 600s (10 min) | `config.py` — session expiration |
| `OLLAMA_TIMEOUT` | 180s | `config.py` — LLM generation timeout |
| `RATE_LIMIT` | 3.0s | `bot/handlers.py` — per-user cooldown |
| `MAX_CONCURRENT_GENERATIONS` | 1 | `bot/handlers.py` — generation semaphore |
| `distance_threshold` | 0.9 | `rag/retriever.py` — max cosine distance for chunks |
| `chunk_size` / `chunk_overlap` | 800 / 150 | `rag/loader.py` — text splitting params |
| `temperature` | 0.5 | `rag/chain.py` — LLM sampling temperature |
| `num_predict` | 512 | `rag/chain.py` — max generated tokens |

---

## 📄 License

This project is provided as-is for educational and portfolio purposes.
]]>
