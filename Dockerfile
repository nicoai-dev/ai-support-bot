# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей (отдельным слоем для кеширования)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект (.dockerignore исключает секреты и ненужное)
COPY . .

# Создаем папки для данных
RUN mkdir -p data/db logs

# Запуск от непривилегированного пользователя (безопасность)
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# Команда запуска
CMD ["python", "main.py"]
