import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from bot.handlers import router
from rag.retriever import build_index
from bot.memory import memory
from bot.middleware import ErrorHandlingMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def cleanup_loop():
    """Периодическая очистка протухших сессий из памяти."""
    while True:
        try:
            await asyncio.sleep(300)  # Очистка каждые 5 минут
            logging.info("Очистка истёкших сессий памяти...")
            memory.cleanup_expired()
        except asyncio.CancelledError:
            logging.info("Задача очистки памяти остановлена.")
            break
        except Exception as e:
            logging.error(f"Ошибка в цикле очистки памяти: {e}")
            await asyncio.sleep(10)  # Пауза перед повторной попыткой при ошибке

from rag.chain import close_session, check_ollama_health


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    logging.info("🔎 Проверка связи с Ollama...")
    if not await check_ollama_health():
        logging.error("❌ КРИТИЧЕСКАЯ ОШИБКА: Сервис Ollama недоступен! Запустите Ollama и попробуйте снова.")
        # В реальном проде тут можно бросить исключение или завершить процесс
        return

    logging.info("🚀 Обновление индекса базы знаний...")
    await build_index()
    logging.info("🚀 Бот Nico Market запущен!")

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем middleware для обработки ошибок
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
    
    # Запуск поллинга
    try:
        await dp.start_polling(bot)
    finally:
        # Graceful shutdown: отменяем фоновые задачи и закрываем сессии
        logging.info("Завершение работы...")
        cleanup_task.cancel()
        try:
            await asyncio.wait_for(cleanup_task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
            
        from rag.chain import close_session
        await close_session()
        await bot.session.close()
        logging.info("Бот Nico Market успешно остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
