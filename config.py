import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    """Центральная конфигурация приложения.
    
    Все значения читаются из переменных окружения или .env файла.
    Документация по каждому полю — в .env.example.
    """
    
    # === Окружение ===
    ENV: Literal["dev", "staging", "prod"] = "dev"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # === Telegram ===
    BOT_TOKEN: str
    WEBAPP_URL: str = "https://example.lhr.life"
    
    # === LLM Provider ===
    LLM_PROVIDER: Literal["ollama", "openai", "anthropic"] = "ollama"
    
    # Ollama (используется при LLM_PROVIDER=ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:32b"
    OLLAMA_TIMEOUT: int = 300
    
    # OpenAI (используется при LLM_PROVIDER=openai)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_TIMEOUT: int = 120
    
    # Anthropic (используется при LLM_PROVIDER=anthropic)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_TIMEOUT: int = 120
    
    # === Storage ===
    STORAGE_BACKEND: Literal["memory", "postgres"] = "memory"
    DATABASE_URL: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # === Memory ===
    MEMORY_MAX_MESSAGES: int = 4
    MEMORY_SESSION_TTL: int = 600
    
    # === RAG ===
    KNOWLEDGE_BASE_DIR: str = os.path.join(BASE_DIR, "data", "knowledge_base")
    CHROMA_DB_DIR: str = os.path.join(BASE_DIR, "data", "chroma_db")
    RAG_TOP_K: int = 8
    RAG_DISTANCE_THRESHOLD: float = 1.5
    RAG_MAX_CONTEXT_CHARS: int = 12000
    
    # === Контактные данные компании (единый источник правды) ===
    COMPANY_NAME: str = "Nico Market"
    SUPPORT_PHONE: str = "+679 764-2658"
    SUPPORT_EMAIL: str = "support@nicomarket.fj"
    PARTNERS_EMAIL: str = "partners@nicomarket.fj"
    PRESS_EMAIL: str = "press@nicomarket.fj"
    COMPANY_SITE: str = "https://nicomarket.fj"
    COMPANY_TELEGRAM: str = "@NicoMarketOfficial"
    COMPANY_INSTAGRAM: str = "@nicomarket.fj"
    SUPPORT_HOURS: str = "08:00–22:00 (FJT / UTC+12)"
    
    # === Admin ===
    ADMIN_USER_IDS: list[int] = []  # Telegram user_id администраторов
    MANAGER_CHAT_ID: int = 0  # ID чата для уведомлений менеджерам
    
    # === Rate Limiting ===
    RATE_LIMIT_SECONDS: float = 3.0
    MAX_MESSAGE_LENGTH: int = 1000
    MAX_CONCURRENT_GENERATIONS: int = 1
    
    # === LLM Generation ===
    LLM_TEMPERATURE: float = 0.5
    LLM_MAX_TOKENS: int = 768
    LLM_CONTEXT_WINDOW: int = 16384
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    @property
    def is_prod(self) -> bool:
        return self.ENV == "prod"
    
    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"
    
    @property
    def known_emails(self) -> set[str]:
        """Все известные email-адреса компании (для guardrails)."""
        return {self.SUPPORT_EMAIL, self.PARTNERS_EMAIL, self.PRESS_EMAIL}
    
    @property
    def known_contacts(self) -> dict[str, str]:
        """Все контакты компании (для guardrails)."""
        return {
            "phone": self.SUPPORT_PHONE,
            "email_support": self.SUPPORT_EMAIL,
            "email_partners": self.PARTNERS_EMAIL,
            "email_press": self.PRESS_EMAIL,
            "site": self.COMPANY_SITE,
            "telegram": self.COMPANY_TELEGRAM,
            "instagram": self.COMPANY_INSTAGRAM,
        }


try:
    settings = Settings()
except Exception as e:
    print("\n" + "="*50)
    print(f"[!] ОШИБКА ИНИЦИАЛИЗАЦИИ КОНФИГА: {e}")
    print("Убедитесь, что вы создали файл .env и добавили в него BOT_TOKEN.")
    print("="*50 + "\n")
    exit(1)

# Обратная совместимость — модульные переменные (DEPRECATED, будут удалены)
# TODO: постепенно мигрировать весь код на settings.X
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
