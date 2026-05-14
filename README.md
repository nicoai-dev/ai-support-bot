# 🤖 AI Support Bot v2.0 (Nico Market Edition)

[Русская версия (RU)](README_RU.md) | **English (EN)**

> Smart Telegram support bot for e-commerce, powered by RAG (Retrieval-Augmented Generation) and local LLM.

![Demo](demo.gif)

## ✨ Features

- 🧠 **Smart Answers (RAG)**: Retrieves information from the knowledge base (.txt files) to answer based on provided context.
- 💬 **Conversation Memory**: Remembers up to 10 last messages, handles follow-up questions (session context).
- ⚡ **Real-time Streaming**: Answers are typed in real-time, ChatGPT-style (stream generation).
- 🌍 **Multilingual RAG**: Uses a multilingual embedding model for precise search in various languages.
- 🔒 **Full Privacy**: All data and LLM (Ollama) run locally on your server. No external AI APIs.
- 🚀 **Async Engine**: Built with a fully asynchronous architecture using `aiogram 3.x` and `aiohttp`.

## 🛠️ Tech Stack

- **Python 3.14+**
- **aiogram 3.x** — Telegram Bot API
- **Ollama + Qwen 32B** — Local LLM
- **ChromaDB** — Vector Database
- **Sentence Transformers** — Multilingual embeddings (`paraphrase-multilingual-MiniLM-L12-v2`)
- **aiohttp** — Async HTTP requests (Singleton session)

## 🚀 Quick Start

### 1. Prerequisites
- Install [Ollama](https://ollama.com/) and pull a model: `ollama pull qwen2.5-coder:32b`.
- Get a bot token from [@BotFather](https://t.me/BotFather).

### 2. Installation
```bash
git clone https://github.com/your-username/ai-support-bot.git
cd ai-support-bot
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env      # Set your BOT_TOKEN in .env
```

### 3. Add Knowledge Base
Place your `.txt` files (FAQ, rules, product descriptions) into `data/knowledge_base/`. The bot will automatically index them on startup.

### 4. Run
```bash
python main.py
```

## 🎮 Commands

- `/start` — Launch and main menu.
- `/help` — How to use the bot.
- `/new` — Reset conversation memory (start a new topic).

## ⚙️ Configuration
All settings (timeouts, memory limits, model names) are located in `config.py`.

---
*Developed for Nico Market as a demonstration of local AI assistant capabilities.*
