import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from bot.handlers import router
from rag.retriever import build_index
from bot.memory import memory

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def cleanup_loop():
    """Периодическая очистка протухших сессий из памяти."""
    while True:
        await asyncio.sleep(300)  # Очистка каждые 5 минут
        logging.info("Очистка истёкших сессий памяти...")
        memory.cleanup_expired()

async def main():
    logging.info("Обновление индекса базы знаний...")
    build_index()

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(router)

    logging.info("Бот Nico Market запущен!")
    
    # Запускаем задачу очистки памяти в фоне
    asyncio.create_task(cleanup_loop())
    
    # Запуск поллинга
    try:
        await dp.start_polling(bot)
    finally:
        from rag.chain import close_session
        await close_session()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
