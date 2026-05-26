# === Stage 1: Builder — установка зависимостей ===
FROM python:3.10-slim AS builder

WORKDIR /build

# Системные зависимости для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# === Stage 2: Runtime — финальный образ ===
FROM python:3.10-slim AS runtime

WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /install /usr/local

# Создаём непривилегированного пользователя
RUN useradd -m -s /bin/bash botuser

# Копируем проект (.dockerignore исключает секреты)
COPY . .

# Создаём директории для данных
RUN mkdir -p data/db logs && chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# Метаданные
LABEL maintainer="Nico Market <support@nicomarket.fj>"
LABEL description="AI Support Bot — Telegram RAG assistant"

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=5)"

CMD ["python", "main.py"]
