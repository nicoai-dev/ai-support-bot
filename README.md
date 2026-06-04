# AI Support Bot — Nico Market

[![Russian](https://img.shields.io/badge/🇷🇺_Русский-blue.svg)](README_RU.md)
[![English](https://img.shields.io/badge/🇬🇧_English-red.svg)](README.md)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![aiogram 3.x](https://img.shields.io/badge/aiogram-3.x-009688.svg)](https://docs.aiogram.dev/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-black.svg)](https://ollama.ai/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)

A production-ready AI support assistant for Telegram built on a **RAG (Retrieval-Augmented Generation)** architecture. Supports fully local execution via **Ollama** (for maximum data privacy) or cloud providers (**OpenAI** and **Anthropic**).

> **TL;DR:** A Telegram bot that answers customer questions about a store using a local or cloud LLM + vector search over a knowledge base, with streaming responses, anti-hallucination guardrails, a built-in Mini App storefront, and a one-click orchestrator that manages the bot, web server, and SSH tunnel automatically.

---

## ✨ Key Features

### 🧠 Advanced Hybrid RAG Pipeline
- **Hybrid Search**: Combines semantic Vector search (ChromaDB using `paraphrase-multilingual-MiniLM-L12-v2`) and Lexical search (custom high-performance `BM25Index`) for maximum precision and recall.
- **RRF Fusion**: Integrates vector and lexical search lists using **Reciprocal Rank Fusion (RRF)**.
- **Cross-Encoder Reranking**: Utilizes `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` to perform deep neural reranking of candidate chunks.
- **Active Query Expansion**: LLM-driven query rewriting (`expand_query`) paraphrases user questions into 3 distinct variations to capture all semantic facets.
- **Context-Aware Retrieval**: Dynamically reconstructs the search query using the last 4 conversational turns to resolve ambiguities in multi-turn dialogues.
- **Distance Filtering**: Cosine distance filtering (threshold `1.5` for hybrid compatibility) keeps search results precise.

### 🛡️ Anti-Hallucination System (Multi-Layer)
1. **System Prompt**: 6 strict constraints baked into the LLM context, including local-only grounding, Russian-only output, category-level grouping for general topics.
2. **Programmatic Guardrails** (`rag/guardrails.py`): Real-time response post-validation filtering out hallucinated contact details or system instruction leaks.
3. **Multi-level Fallbacks**: If guardrails trigger ≥ 3 violations, or retrieval returns zero valid chunks, the LLM is bypassed and a polite, verified fallback response is served.

### ⚡ Asynchronous Architecture & Task Queuing
- **ARQ Task Offloading**: Heavy search and generation logic is offloaded to a Redis-backed **ARQ async worker process** (`workers/llm_worker.py`), keeping the bot's event loop completely non-blocking.
- **Local Fallback**: Gracefully falls back to inline generation if Redis/ARQ is offline.
- **Concurrency Control**: A semaphore serializes LLM calls to prevent resource thrashing on local host machines.

### ⚕️ Enterprise Observability & Health
- **Structured JSON Logging**: Custom `JSONFormatter` in `main.py` writes machine-readable logs to `logs/bot.jsonl` with automatic rotation.
- **Healthcheck Microservice**: Built-in HTTP server (port `8080`, `/health` endpoint) exposes live status metrics for Ollama and storage connectivity.

### 🛒 Telegram Mini App (WebApp)
- A highly polished storefront built using vanilla HTML/CSS/JS with modern glassmorphism styling.
- Real-time catalog search over 22k+ mock records (`products.json`).
- Live shopping cart, user session injection, and checkout callbacks sending structured transaction data to the bot.

### 🔄 Orchestrator (`run_all.py`)
A comprehensive supervisor process that:
1. **Kills Orphaned Instances**: Cleans up previous runs (Windows-aware).
2. **Bootstraps Stack**: Launches static HTTP catalog server and dynamic SSH tunnel (`localhost.run`).
3. **Auto-manages environment**: Rewrites `.env` with updated public WebApp URL.
4. **Monitors and Recovers**: Runs active ping checks on SSH endpoint and auto-restarts Bot and ARQ Worker processes if they terminate or experience failures.

---

## 📁 Project Structure

```
ai-support-bot/
├── main.py                  # Entrypoint: bot init, polling, background tasks, logging setup
├── config.py                # Pydantic Settings config, database/cache urls, timeout configurations
├── run_all.py               # Process supervisor: manages bot, web server, ARQ worker & SSH tunnel
├── run_all.bat              # Windows orchestrator execution shortcut
├── run_bot.bat              # Windows bot-only execution shortcut
├── bot/
│   ├── handlers.py          # Command/message handlers, ARQ scheduling, callbacks
│   ├── memory.py            # Chat session memory manager (SQLite/PostgreSQL wrapper)
│   ├── middleware.py        # Global error safety middleware
│   ├── cache.py             # RedisCache wrapper for session caching
│   ├── health.py            # Microservice health check logic
│   ├── storage.py           # Abstract base class for storage adapters
│   └── storage_postgres.py  # Enterprise PostgreSQL storage implementation with asyncpg
├── rag/
│   ├── loader.py            # Custom recursive document splitter
│   ├── retriever.py         # Vector+BM25 Hybrid search, RRF fusion, and Reranking controller
│   ├── chain.py             # LLM orchestration, query expansion, prompts, system instructions
│   ├── guardrails.py        # Safety regex post-processing rules
│   ├── bm25_index.py        # Lightweight custom TF-IDF BM25 index implementation
│   └── reranker.py          # CrossEncoder reranking layer
├── workers/
│   └── llm_worker.py        # ARQ Worker performing asynchronous search & inference tasks
├── data/
│   ├── knowledge_base/      # Granular source knowledge text files
│   ├── chroma_db/           # Persistent local vector storage folder (Git ignored)
│   ├── prompts/             # System prompt template (system.txt)
│   └── memory.db            # SQLite persistent memory file (Git ignored)
├── logs/
│   └── bot.jsonl            # Machine-readable rotating logs output (Git ignored)
├── webapp/
│   ├── index.html           # Storefront Mini App layout
│   ├── style.css            # Glassmorphism frontend styles
│   ├── app.js               # WebApp cart, search, and Telegram integration logic
│   └── products.json        # Static mock database
├── tests/
│   └── test_guardrails.py   # Automated safety validations
├── Dockerfile               # Production image template
├── docker-compose.yml       # Stack runner setup
├── requirements.txt         # Project requirements manifest
├── .env.example             # Sandbox configurations template
└── .gitignore               # Excludes secrets, local DBs, user uploads, logs, cache
```

---

## 🛠 Technology Stack

| Layer | Technology |
|-------|-----------|
| **Bot Framework** | `aiogram 3.x` (Python 3.10+) |
| **LLM Engine** | Multi-Provider: `Ollama` (default, e.g. `qwen2.5-coder:32b`), `OpenAI` (`gpt-4o-mini`), `Anthropic` (`claude-3-5-sonnet`) |
| **Embeddings** | `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`) |
| **Vector Database** | `ChromaDB` (persistent, cosine distance) |
| **Lexical Search** | Custom `BM25Index` (tf-idf based ranker) |
| **Reranker Engine**| `sentence-transformers` (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) |
| **Background Tasks**| `arq` (Redis async queuing) + `redis` caching |
| **Database Storage**| `asyncpg` + PostgreSQL (durable sessions) or local SQLite |
| **Configuration**  | `pydantic-settings` (v2 env configurations validator) |
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
| `LLM_PROVIDER` | `ollama` | LLM provider: `ollama`, `openai`, or `anthropic` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5-coder:32b` | LLM model name |
| `OPENAI_API_KEY` | — | OpenAI API key (required if `LLM_PROVIDER=openai`) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (required if `LLM_PROVIDER=anthropic`) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Anthropic model name |
| `WEBAPP_URL` | `https://nico-market-catalog.loca.lt` | WebApp public URL (auto-updated by `run_all.py`) |
| `STORAGE_BACKEND` | `memory` | Session storage adapter: `memory` (SQLite) or `postgres` |
| `DATABASE_URL` | — | Connection string for PostgreSQL backend |
| `REDIS_URL` | `redis://localhost:6379/0` | Connection string for Redis cache & ARQ worker |

---

## 📝 Knowledge Base

The bot's knowledge comes from plain `.txt` files in `data/knowledge_base/`. On startup, they are:
1. Loaded and split into chunks (800 chars, 150 overlap).
2. Indexed using `ChromaDB` (vector embeddings) and `BM25Index` (lexical index).
3. Used at runtime with RRF fusion and neural cross-encoder reranking.

Current knowledge base structure:
| Categories | Source Files | Content |
|------------|--------------|---------|
| **About Company** | `about_company.txt`, `about_history.txt` | Company info, history, core missions, milestones. |
| **Bot Persona** | `bot_persona_rules.txt`, `bot_persona_story.txt` | Persona guidelines, tone constraints, styling examples, context boundaries. |
| **Catalog Devices** | `catalog_overview.txt`, `catalog_a1_smartphones.txt` ... `catalog_a7_drones_cameras.txt` | Individual product listings, names, specs, and price ranges split by categories. |
| **Catalog Services** | `catalog_b1_software.txt` ... `catalog_b4_games.txt`, `catalog_c_dev_design.txt`, `catalog_c_support_security.txt` | IT services, web development, custom bots, cloud plans, gaming support details. |
| **Support Contacts** | `contacts.txt` | Support phone numbers, support emails, headquarters location, operating hours. |
| **FAQ Sections** | `faq_general.txt`, `faq_orders_delivery.txt`, `faq_returns_warranty.txt` | Modularized answers to frequently asked customer questions. |
| **Policies** | `policy_delivery.txt`, `policy_payment.txt`, `policy_returns.txt`, `policy_warranty.txt` | Precise legal conditions on payment methods, delivery durations, return windows. |
| **Subscriptions** | `subscriptions.txt` | Premium SaaS tiers, SLA options, pricing, and features. |
| **Team members** | `team.txt` | Roles, names, and departments of core team members. |

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
| `/privacy` | Privacy Policy summary |

**Admin Commands (Requires ID in `ADMIN_USER_IDS`):**
| Command | Description |
|---------|-------------|
| `/admin` | Show admin panel |
| `/stats` | View order and revenue statistics |
| `/orders` | View latest 10 orders |
| `/reload_kb`| Hot-reload knowledge base from txt files |
| `/health_check`| View system health |
| `/sessions`| View active user sessions |

Inline buttons: **Order status**, **Return policy**, **Contact manager**.

---

## ⚙️ Configuration Constants

| Constant | Value | Location | Description |
|----------|-------|----------|-------------|
| `MEMORY_MAX_MESSAGES` | 4 | `config.py` | max messages kept in active memory context |
| `MEMORY_SESSION_TTL` | 600s (10 min) | `config.py` | session timeout |
| `OLLAMA_TIMEOUT` | 300s | `config.py` | LLM generation timeout |
| `RATE_LIMIT` | 3.0s | `bot/handlers.py` | per-user rate limit interval |
| `distance_threshold` | 1.5 | `rag/retriever.py` | threshold for hybrid vector filter |
| `chunk_size` / `chunk_overlap` | 800 / 150 | `rag/loader.py` | text chunk parameters |
| `temperature` | 0.5 | `rag/chain.py` | LLM temperature |
| `num_predict` | 768 | `rag/chain.py` | maximum generated tokens limit |
| `num_ctx` | 16384 | `rag/chain.py` | model context window allocation size |

---

## 📄 License

This project is provided as-is for educational and portfolio purposes.
