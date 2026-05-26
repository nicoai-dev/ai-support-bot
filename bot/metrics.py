"""Prometheus метрики для мониторинга бота."""
from prometheus_client import Counter, Histogram, Gauge, Info

# Информация о боте
bot_info = Info("bot", "Информация о боте")

# Сообщения
messages_total = Counter(
    "bot_messages_total",
    "Общее количество обработанных сообщений",
    ["type"],  # text, command, webapp, rate_limited
)

# LLM
llm_requests_total = Counter(
    "bot_llm_requests_total",
    "Общее количество запросов к LLM",
    ["provider", "status"],  # success, error
)

llm_latency_seconds = Histogram(
    "bot_llm_latency_seconds",
    "Время генерации ответа LLM",
    buckets=[1, 2, 5, 10, 20, 30, 60, 120, 300],
)

# RAG
rag_retrieval_latency = Histogram(
    "bot_rag_retrieval_latency_seconds",
    "Время поиска чанков",
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5],
)

# Chunks
rag_chunks_found = Histogram(
    "bot_rag_chunks_found",
    "Количество найденных чанков на запрос",
    buckets=[0, 1, 2, 3, 5, 8, 10],
)

# Guardrails
guardrails_triggered = Counter(
    "bot_guardrails_triggered_total",
    "Количество срабатываний guardrails",
    ["type"],  # phone, email, url, leak, fallback
)

# Активные пользователи
active_sessions = Gauge(
    "bot_active_sessions",
    "Количество активных сессий в памяти",
)

# Ошибки
errors_total = Counter(
    "bot_errors_total",
    "Общее количество ошибок",
    ["component"],  # handler, llm, rag, storage
)
