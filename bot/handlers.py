import logging
import time
import asyncio
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from rag.retriever import search
from rag.chain import generate_answer_stream
from bot.memory import memory

router = Router()

RATE_LIMIT = 3.0  # Секунды между сообщениями
MAX_CONCURRENT_GENERATIONS = 2
generation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)


def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📦 Мой заказ", callback_data="order_status"))
    builder.row(types.InlineKeyboardButton(text="🔄 Возврат товара", callback_data="return_policy"))
    builder.row(types.InlineKeyboardButton(text="📞 Связаться с менеджером", callback_data="contact_manager"))
    return builder.as_markup()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в Nico Market!\n\n"
        "Я ваш виртуальный помощник. Задайте мне любой вопрос о наших товарах или правилах магазина.\n\n"
        "Чем я могу вам помочь сегодня?",
        reply_markup=get_main_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "💡 **Как пользоваться ботом:**\n\n"
        "1. Просто напишите ваш вопрос текстом.\n"
        "2. Я помню контекст диалога (например, если вы уточняете детали предыдущего вопроса).\n"
        "3. Если хотите начать новую тему, используйте /new.\n\n"
        "Или выберите нужный раздел ниже:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


@router.message(Command("new"))
async def cmd_new(message: types.Message):
    memory.clear(message.from_user.id)
    await message.answer("🔄 Контекст диалога сброшен. Начнем сначала!")


@router.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    if callback.data == "order_status":
        await callback.message.answer("🔎 Чтобы узнать статус заказа, пожалуйста, напишите его номер (например: Заказ #12345).")
    elif callback.data == "return_policy":
        await callback.message.answer("🔄 У нас действует возврат в течение 14 дней при сохранности товарного вида. Что именно вы хотите вернуть?")
    elif callback.data == "contact_manager":
        await callback.message.answer("📞 Наш менеджер на связи по телефону: +7 (999) 000-00-00.\nГрафик работы: ежедневно с 9:00 до 21:00.")
    await callback.answer()


@router.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    # Rate limiting через объект memory
    if not memory.check_rate_limit(user_id, RATE_LIMIT):
        await message.answer("⚠️ Вы отправляете сообщения слишком часто. Пожалуйста, подождите пару секунд.")
        return

    # Обработка нетекстовых сообщений
    if not message.text:
        await message.answer("Я пока работаю только с текстом. Пожалуйста, напишите ваш вопрос.")
        return

    # Проверка длины сообщения
    if len(message.text) > 1000:
        await message.answer("Ваше сообщение слишком длинное. Пожалуйста, сократите его до 1000 символов.")
        return

    # Показываем статус "печатает"
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    processing_msg = await message.answer("🔄 Обрабатываю ваш запрос...")

    try:
        chat_history = memory.get_history(user_id)
        
        # 1. Поиск релевантных чанков
        chunks = await search(message.text, top_k=8, distance_threshold=0.9)
        
        # ЛОГ ДЛЯ ОТЛАДКИ (увидишь в консоли, что нашел бот)
        if chunks:
            logging.info(f"🔎 Найдено чанков: {len(chunks)}")
            for i, c in enumerate(chunks):
                logging.info(f"Чанк {i+1}: {c['text'][:50]}...")
        else:
            logging.warning("⚠️ Ничего не найдено в базе знаний! Использую fallback.")
            fallback_answer = (
                "К сожалению, у меня нет точной информации по этому вопросу в текущей базе знаний. "
                "Давайте я соединю вас с менеджером — он точно во всём разберётся!\n\n"
                "📞 +679 764-2658 (08:00–22:00)\n"
                "📧 support@nicomarket.fj"
            )
            await processing_msg.edit_text(fallback_answer)
            memory.add_message(user_id, "user", message.text)
            memory.add_message(user_id, "assistant", fallback_answer)
            return

        # 2. Потоковая генерация ответа
        full_answer = ""
        last_edit_time = time.time()
        
        async with generation_semaphore:
            async for partial_answer in generate_answer_stream(message.text, chunks, chat_history):
                if not partial_answer:
                    continue
                    
                full_answer = partial_answer
                # Обновляем каждые 1.5 сек для безопасности (лимиты Telegram)
                now = time.time()
                if now - last_edit_time > 1.5:
                    try:
                        await processing_msg.edit_text(partial_answer + " ▌")
                        last_edit_time = now
                    except Exception as edit_error:
                        # Если поймали флуд или другую ошибку редактирования — просто пропускаем шаг
                        logging.debug(f"Пропуск обновления стриминга: {edit_error}")
                        pass

        from rag.guardrails import validate_response

        # Финальный текст и валидация
        if full_answer:
            validated_answer, warnings = validate_response(full_answer)
            
            if warnings:
                logging.warning(f"⚠️ Guardrails сработали для user {user_id}: {warnings}")
                # Если слишком много подозрений — подменяем на безопасный ответ
                if len(warnings) >= 3:
                    validated_answer = (
                        "Прошу прощения, я не уверен в точности своего ответа на этот вопрос. "
                        "Чтобы не ввести вас в заблуждение, лучше уточните это у нашего менеджера.\n\n"
                        "📞 +679 764-2658\n📧 support@nicomarket.fj"
                    )
            
            await processing_msg.edit_text(validated_answer)
            
            # Лог для аудита галлюцинаций
            logging.info(
                f"📊 AUDIT | user={user_id} | "
                f"query='{message.text[:80]}' | "
                f"chunks_found={len(chunks)} | "
                f"guardrail_warnings={len(warnings)} | "
                f"answer_len={len(validated_answer)}"
            )
            
            # Сохраняем диалог в память
            memory.add_message(user_id, "user", message.text)
            memory.add_message(user_id, "assistant", validated_answer)
        else:
            await processing_msg.edit_text(
                "К сожалению, не удалось сформировать ответ. Попробуйте переформулировать вопрос или обратитесь к менеджеру по телефону +679 764-2658."
            )

    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        await processing_msg.edit_text(
            "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже или свяжитесь с поддержкой Nico Market."
        )
