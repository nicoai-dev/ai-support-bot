import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from bot.handlers import router
from rag.retriever import build_index
from bot.memory import memory
from bot.middleware import ErrorHandlingMiddleware

import logging.handlers
import json
import sys
import os

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging(log_dir: str = "logs", level: str = "INFO"):
    root = logging.getLogger()
    root.setLevel(getattr(logging, level))
    
    # Console — human-readable
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    root.addHandler(console)
    
    # File — JSON, с ротацией
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        f"{log_dir}/bot.jsonl", maxBytes=50_000_000, backupCount=5
    )
    file_handler.setFormatter(JSONFormatter())
    root.addHandler(file_handler)

from config import settings
setup_logging(level=settings.LOG_LEVEL)

async def cleanup_loop():
    """Периодическая очистка протухших сессий из памяти."""
    while True:
        try:
            await asyncio.sleep(300)  # Очистка каждые 5 минут
            logging.info("Очистка истёкших сессий памяти...")
            await memory.cleanup_expired()
        except asyncio.CancelledError:
            logging.info("Задача очистки памяти остановлена.")
            break
        except Exception as e:
            logging.error(f"Ошибка в цикле очистки памяти: {e}")
            await asyncio.sleep(10)  # Пауза перед повторной попыткой при ошибке

async def wakeup_loop():
    """Фоновая задача для периодического пробуждения event loop на Windows,
    чтобы корректно и быстро обрабатывался Ctrl+C.
    """
    while True:
        try:
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break

from rag.chain import close_session, check_ollama_health


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    from config import STORAGE_BACKEND
    if STORAGE_BACKEND == "postgres":
        from bot.memory import init_postgres_memory
        logging.info("Подключение к PostgreSQL...")
        await init_postgres_memory()
    logging.info("🔎 Проверка связи с Ollama...")
    if not await check_ollama_health():
        logging.error("❌ КРИТИЧЕСКАЯ ОШИБКА: Сервис Ollama недоступен! Запустите Ollama и попробуйте снова.")
        # В реальном проде тут можно бросить исключение или завершить процесс
        return

    logging.info("🚀 Обновление индекса базы знаний...")
    await build_index()
    
    from bot.health import start_health_server
    global health_runner
    health_runner = await start_health_server()
    logging.info("⚕️ Healthcheck server запущен на порту 8080")
    
    logging.info("🚀 Бот Nico Market запущен!")

    # Инициализация ARQ
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        from config import REDIS_URL
        import bot.handlers

        bot.handlers.arq_pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
        logging.info("✅ ARQ Pool инициализирован")
    except Exception as e:
        logging.warning(f"⚠️ Ошибка инициализации ARQ: {e}")

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем middleware для correlation ID и обработки ошибок
    from bot.middleware import RequestContextMiddleware
    dp.update.outer_middleware(RequestContextMiddleware())
    dp.update.outer_middleware(ErrorHandlingMiddleware())

    # Регистрация роутеров и событий
    dp.include_router(router)
    dp.startup.register(on_startup)
    
    # Запускаем задачу очистки памяти в фоне
    cleanup_task = asyncio.create_task(cleanup_loop())
    
    # Мониторинг падения задачи
    def handle_task_result(task):
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            logging.exception("Критическая ошибка в фоновой задаче очистки памяти:")

    cleanup_task.add_done_callback(handle_task_result)
    
    # Запускаем фоновую wakeup-задачу на Windows для мгновенной реакции на Ctrl+C
    import sys
    wakeup_task = None
    if sys.platform == "win32":
        wakeup_task = asyncio.create_task(wakeup_loop())
    
    # Запуск поллинга
    try:
        await dp.start_polling(bot)
    finally:
        # Graceful shutdown: отменяем фоновые задачи и закрываем сессии
        logging.info("Завершение работы...")
        cleanup_task.cancel()
        if wakeup_task:
            wakeup_task.cancel()
            
        try:
            await asyncio.wait_for(cleanup_task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
            
        from rag.chain import close_session
        await close_session()
        await bot.session.close()
        
        global health_runner
        if 'health_runner' in globals() and health_runner:
            await health_runner.cleanup()
            
        logging.info("Бот Nico Market успешно остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
