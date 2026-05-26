#!/bin/bash
# =============================================
# Бэкап PostgreSQL для AI Support Bot
# Запуск: ./scripts/backup_pg.sh
# Cron:   0 3 * * * /path/to/backup_pg.sh
# =============================================

set -euo pipefail

# Конфигурация
BACKUP_DIR="${BACKUP_DIR:-./backups}"
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-bot}"
PG_DB="${PG_DB:-nicomarket}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Имя файла с датой
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/nicomarket_${TIMESTAMP}.sql.gz"

# Создаём директорию если не существует
mkdir -p "${BACKUP_DIR}"

echo "🗄️  Начинаю бэкап PostgreSQL..."
echo "   Host: ${PG_HOST}:${PG_PORT}"
echo "   DB:   ${PG_DB}"
echo "   File: ${BACKUP_FILE}"

# Выполняем бэкап
if command -v docker &> /dev/null; then
    # Если запущен в Docker-окружении
    docker exec ai-support-bot-postgres-1 \
        pg_dump -U "${PG_USER}" "${PG_DB}" | gzip > "${BACKUP_FILE}"
else
    # Локальный pg_dump
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
        -h "${PG_HOST}" \
        -p "${PG_PORT}" \
        -U "${PG_USER}" \
        "${PG_DB}" | gzip > "${BACKUP_FILE}"
fi

# Проверяем что файл создан и не пуст
if [ -s "${BACKUP_FILE}" ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "✅ Бэкап создан: ${BACKUP_FILE} (${SIZE})"
else
    echo "❌ Бэкап пуст или не создан!"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# Удаляем старые бэкапы
DELETED=$(find "${BACKUP_DIR}" -name "nicomarket_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete -print | wc -l)
if [ "${DELETED}" -gt 0 ]; then
    echo "🧹 Удалено старых бэкапов: ${DELETED} (retention: ${RETENTION_DAYS} дней)"
fi

echo "✅ Бэкап завершён"
