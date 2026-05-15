# AI Support Bot (Nico Market)

[![Russian](https://img.shields.io/badge/Language-Russian-blue.svg)](README_RU.md)
[![English](https://img.shields.io/badge/Language-English-red.svg)](README.md)

An advanced, production-ready AI support assistant built for Telegram. It leverages a Retrieval-Augmented Generation (RAG) architecture, fully local LLMs via Ollama, and high-precision semantic search using ChromaDB.

## 🚀 Key Features

- **100% Local Processing**: Uses Ollama (e.g., Qwen 2.5 Coder 32b) to ensure maximum data privacy and zero recurring API costs.
- **Advanced RAG Architecture**: 
  - Uses `SentenceTransformers` and `ChromaDB` for semantic context retrieval.
  - Optimized with `cosine` distance metrics and normalized embeddings for high precision.
  - **Context-Aware Search**: Dynamically analyzes the user's conversational history to understand multi-turn follow-up questions.
- **Anti-Hallucination Mechanisms**: Strict system prompts prevent the model from inventing non-existent products, services, or fake URLs. If it's not in the knowledge base, the bot admits it doesn't know.
- **Asynchronous & Non-Blocking**: Built on `aiogram 3.x` with `asyncio.to_thread` executors. Heavy vector calculations (embeddings) run in separate threads, preventing event-loop freezing.
- **Production-Ready & Stable**: 
  - Global `ErrorHandlingMiddleware` catches exceptions and politely notifies users.
  - Background memory cleanup loop automatically purges stale user sessions.
  - Docker & Docker Compose integration for seamless 1-click deployment.

## 🛠 Technology Stack

- **Framework**: `aiogram 3.x` (Python 3.10+)
- **Vector Database**: `ChromaDB`
- **Embeddings**: `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`)
- **LLM Engine**: `Ollama` 
- **Networking**: `aiohttp` (Singleton session pattern)

## 📦 Quick Start

### 1. Prerequisites
- Docker and Docker Compose installed.
- [Ollama](https://ollama.ai/) installed and running locally.

### 2. Setup
1. Clone the repository.
2. Copy `.env.example` to `.env` and insert your Telegram `BOT_TOKEN`.
   ```env
   BOT_TOKEN=your_telegram_bot_token_here
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   OLLAMA_MODEL=qwen2.5-coder:32b
   ```
3. Place your knowledge base text files (.txt, .md) into the `data/knowledge_base/` directory.

### 3. Run
Launch the application using Docker Compose:
```bash
docker-compose up --build -d
```
The bot will automatically check Ollama's health, build the vector index, and start polling.
