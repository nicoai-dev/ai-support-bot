import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from bot.handlers import router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(router)

    logging.info("Запуск бота...")
    
    # Запуск поллинга
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
