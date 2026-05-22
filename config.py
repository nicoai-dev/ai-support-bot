import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    WEBAPP_URL: str = "https://nico-market-catalog.loca.lt"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:32b"
    OLLAMA_TIMEOUT: int = 300
    
    # Storage
    STORAGE_BACKEND: Literal["memory", "postgres"] = "memory"
    DATABASE_URL: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Memory
    MEMORY_MAX_MESSAGES: int = 4
    MEMORY_SESSION_TTL: int = 600
    
    # Paths
    KNOWLEDGE_BASE_DIR: str = os.path.join(BASE_DIR, "data", "knowledge_base")
    CHROMA_DB_DIR: str = os.path.join(BASE_DIR, "data", "chroma_db")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

try:
    settings = Settings()
except Exception as e:
    print("\n" + "="*50)
    print(f"[!] ОШИБКА ИНИЦИАЛИЗАЦИИ КОНФИГА: {e}")
    print("Убедитесь, что вы создали файл .env и добавили в него BOT_TOKEN.")
    print("="*50 + "\n")
    exit(1)

# Сохраняем обратную совместимость для старого кода (пока не везде обновили)
BOT_TOKEN = settings.BOT_TOKEN
OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL
OLLAMA_MODEL = settings.OLLAMA_MODEL
WEBAPP_URL = settings.WEBAPP_URL
KNOWLEDGE_BASE_DIR = settings.KNOWLEDGE_BASE_DIR
CHROMA_DB_DIR = settings.CHROMA_DB_DIR
MEMORY_MAX_MESSAGES = settings.MEMORY_MAX_MESSAGES
MEMORY_SESSION_TTL = settings.MEMORY_SESSION_TTL
OLLAMA_TIMEOUT = settings.OLLAMA_TIMEOUT
STORAGE_BACKEND = settings.STORAGE_BACKEND
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL

