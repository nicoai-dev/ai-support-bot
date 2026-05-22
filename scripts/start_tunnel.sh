#!/bin/sh
# Скрипт запускается в контейнере `tunnel`.
# 1. Поднимает SSH-туннель к localhost.run (порт 80 -> nginx:80)
# 2. Парсит выданный URL и записывает в Redis (ключ webapp:tunnel_url)
# 3. При разрыве — переподключается и обновляет Redis

set -e

NGINX_HOST="${NGINX_HOST:-nginx}"
NGINX_PORT="${NGINX_PORT:-80}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

echo "[tunnel] Ожидаем готовности Redis..."
until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping | grep -q PONG; do
  sleep 1
done
echo "[tunnel] Redis готов."

connect_tunnel() {
  echo "[tunnel] Подключаемся к localhost.run..."
  
  # Запускаем SSH и захватываем вывод в фоне
  ssh \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=15 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -R "80:${NGINX_HOST}:${NGINX_PORT}" \
    nokey@localhost.run 2>&1 | while IFS= read -r line; do
      echo "[tunnel] $line"
      # Ищем URL вида https://xxx.lhr.life
      if echo "$line" | grep -qE "https://[a-zA-Z0-9-]+\.lhr\.life"; then
        URL=$(echo "$line" | grep -oE "https://[a-zA-Z0-9-]+\.lhr\.life")
        echo "[tunnel] ✅ Получен URL: $URL"
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" SET webapp:tunnel_url "$URL" EX 86400
        echo "[tunnel] URL записан в Redis."
      fi
    done
  
  echo "[tunnel] SSH-соединение разорвано. Переподключение через 5 сек..."
  sleep 5
}

# Основной цикл с автоматическим переподключением
while true; do
  connect_tunnel
done
