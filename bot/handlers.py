from aiogram import Router, types
from aiogram.filters import CommandStart, Command

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я твой AI-ассистент.\n\n"
        "Я могу отвечать на вопросы, используя базу знаний.\n"
        "Просто напиши мне что-нибудь!\n\n"
        "Доступные команды:\n"
        "/help — получить справку"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "💡 Как это работает?\n\n"
        "1. Ты задаешь вопрос.\n"
        "2. Я ищу информацию в загруженных документах.\n"
        "3. Я формирую ответ с помощью нейросети.\n\n"
        "⚠️ Сейчас я работаю в режиме эхо-бота, RAG будет подключен завтра!"
    )

@router.message()
async def handle_message(message: types.Message):
    await message.answer("🔄 Обрабатываю твой запрос...")
    # Здесь в будущем будет логика RAG
    await message.answer(f"Я получил твое сообщение: *{message.text}*\n\nИнтеграция с базой знаний и Ollama будет в следующем шаге!", parse_mode="Markdown")
