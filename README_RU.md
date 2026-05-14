# 🤖 AI Support Bot v2.0 (Nico Market Edition)

**Русская версия (RU)** | [English (EN)](README.md)

> Умный Telegram-бот поддержки для интернет-магазина, работающий на базе RAG (Retrieval-Augmented Generation) и локальной LLM.

![Demo](demo.gif)

## ✨ Основные фишки

- 🧠 **Умные ответы (RAG)**: Бот ищет информацию в базе знаний (.txt файлы) и отвечает на основе найденного контекста.
- 💬 **Память диалога**: Помнит до 10 последних сообщений, понимает уточняющие вопросы (контекст сессии).
- ⚡ **Real-time Streaming**: Ответы печатаются в реальном времени, как в ChatGPT (потоковая генерация).
- 🌍 **Multilingual RAG**: Использует мультиязычную модель эмбеддингов для точного поиска на русском языке.
- 🔒 **Полная приватность**: Все данные и LLM (Ollama) работают локально на вашем сервере.
- 🚀 **Async Engine**: Полностью асинхронная архитектура на `aiogram 3.x` и `aiohttp`.

## 🛠️ Технологический стек

- **Python 3.14+**
- **aiogram 3.x** — Telegram Bot API
- **Ollama + Qwen 32B** — Локальная нейросеть
- **ChromaDB** — Векторная база данных
- **Sentence Transformers** — Мультиязычные эмбеддинги (`paraphrase-multilingual-MiniLM-L12-v2`)
- **aiohttp** — Асинхронные HTTP-запросы (Singleton session)

## 🚀 Быстрый старт

### 1. Подготовка
- Установите [Ollama](https://ollama.com/) и скачайте модель: `ollama pull qwen2.5-coder:32b`.
- Получите токен бота у [@BotFather](https://t.me/BotFather).

### 2. Установка
```bash
git clone https://github.com/your-username/ai-support-bot.git
cd ai-support-bot
python -m venv venv
source venv/bin/activate  # Или venv\Scripts\activate на Windows
pip install -r requirements.txt
cp .env.example .env      # Укажите свой BOT_TOKEN в .env
```

### 3. Наполнение базы знаний
Просто закиньте ваши `.txt` файлы (правила магазина, FAQ, описание товаров) в папку `data/knowledge_base/`. Бот сам проиндексирует их при запуске.

### 4. Запуск
```bash
python main.py
```

## 🎮 Команды бота

- `/start` — Запуск и главное меню.
- `/help` — Инструкция по использованию.
- `/new` — Сброс памяти диалога (начать новую тему).

## ⚙️ Конфигурация
Все настройки (таймауты, лимиты памяти, модель) находятся в `config.py`.

---
*Разработано для Nico Market в качестве демонстрации возможностей локальных AI-ассистентов.*
