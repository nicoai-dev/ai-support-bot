import logging
import time
import asyncio
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import config
from rag.retriever import search
from rag.chain import generate_answer_stream
import bot.memory

router = Router()

from arq import create_pool
from arq.connections import RedisSettings

RATE_LIMIT = 3.0  # Секунды между сообщениями
MAX_CONCURRENT_GENERATIONS = 1
generation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)

arq_pool = None


async def get_reply_keyboard(user_id: int = 0, first_name: str = "Гость", photo_file_id: str = ""):
    """Сформировать клавиатуру с кнопкой открытия WebApp.
    
    БЕЗОПАСНОСТЬ: НЕ передаём BOT_TOKEN, photo URL или другие секреты через query string.
    WebApp получает данные пользователя напрямую из Telegram SDK (initDataUnsafe.user).
    В URL передаём только first_name для быстрого приветствия до инициализации SDK.
    """
    from urllib.parse import quote
    encoded_name = quote(first_name or "Гость")

    # Читаем актуальный URL туннеля из Redis (пишет tunnel-контейнер).
    # Fallback — значение из .env (config.WEBAPP_URL).
    webapp_url = config.WEBAPP_URL
    try:
        from bot.cache import redis_cache
        tunnel_url = await redis_cache.get("webapp:tunnel_url")
        if tunnel_url:
            webapp_url = tunnel_url
    except Exception:
        pass  # Redis недоступен — берём из конфига

    # ВАЖНО: НЕ передаём user_id и photo_url через URL — это PII и потенциальная утечка.
    # WebApp получит user данные через Telegram.WebApp.initDataUnsafe.user
    url = f"{webapp_url}?first_name={encoded_name}"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Каталог Nico Market", web_app=WebAppInfo(url=url))]
        ],
        resize_keyboard=True
    )


from bot.cache import redis_cache

async def get_user_photo_url(message: types.Message) -> str:
    """Получить URL аватарки пользователя.
    
    БЕЗОПАСНОСТЬ: Используем file_id вместо прямого URL с токеном.
    file_id безопасен для передачи клиенту — он не содержит BOT_TOKEN.
    Для отображения в WebApp используем Telegram getUserProfilePhotos API
    через file_id, который Telegram сам резолвит в CDN-ссылку.
    """
    cache_key = f"avatar:{message.from_user.id}"
    cached = await redis_cache.get(cache_key)
    if cached:
        return cached

    try:
        photos = await message.bot.get_user_profile_photos(user_id=message.from_user.id, limit=1)
        if photos.total_count > 0:
            # Используем file_id — безопасный идентификатор, не содержащий токен
            file_id = photos.photos[0][-1].file_id
            # Кешируем file_id, а не URL с токеном
            await redis_cache.set(cache_key, file_id, ttl=3600)
            return file_id
    except Exception as e:
        logging.error(f"Ошибка получения аватарки пользователя: {e}")
    return ""


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
        "Я — Нико, цифровой консьерж и первый AI-сотрудник компании. "
        "К Вашим услугам: консультации по ассортименту, помощь с заказами и навигация по правилам магазина.\n\n"
        "Чем могу быть полезен?",
        reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name)
    )
    await message.answer(
        "💡 Для быстрого доступа воспользуйтесь панелью ниже:",
        reply_markup=get_main_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "💡 **Краткое руководство:**\n\n"
        "1. Задайте вопрос текстом — я обработаю его в приоритетном порядке.\n"
        "2. Я сохраняю контекст беседы и учитываю предыдущие уточнения.\n"
        "3. Команда /new — начать диалог с чистого листа.\n\n"
        "Или воспользуйтесь быстрым меню:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


@router.message(Command("new"))
async def cmd_new(message: types.Message):
    await bot.memory.memory.clear(message.from_user.id)
    await message.answer("🔄 Контекст диалога обнулён. Я готов к новому запросу — слушаю Вас.", reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name))


@router.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    if callback.data == "order_status":
        await callback.message.answer("🔎 Для проверки статуса, пожалуйста, укажите номер заказа (например: #12345).")
    elif callback.data == "return_policy":
        await callback.message.answer("🔄 Стандартный срок возврата составляет 14 дней при сохранении товарного вида. Какой товар Вы хотели бы вернуть?")
    elif callback.data == "contact_manager":
        await callback.message.answer(
            "📞 **Служба поддержки Nico Market**\n\n"
            "Живой специалист на связи ежедневно:\n"
            "• **Телефон:** `+679 764-2658`\n"
            "• **Часы работы:** 08:00–22:00 (FJT / UTC+12)\n\n"
            "Вы также можете продолжить диалог со мной — я к Вашим услугам.",
            parse_mode="Markdown"
        )
    await callback.answer()


import json
from aiogram import F

@router.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        items = data.get("items", {})
        total = data.get("total", 0)
        
        if not items:
            await message.answer("🛒 Корзина пуста. Воспользуйтесь каталогом, чтобы выбрать интересующие позиции.", reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name))
            return
            
        receipt = "🛒 **Заказ оформлен**\n\n"
        for item_id, item in items.items():
            receipt += f"• {item['title']} — {item['count']} шт. (${item['price']} / шт.)\n"
            
        receipt += f"\n💵 **Итого к оплате: ${total}**\n\n"
        receipt += (
            "Благодарим за выбор Nico Market! Менеджер свяжется с Вами для подтверждения и уточнения деталей доставки.\n\n"
            "📞 +679 764-2658 (08:00–22:00)\n"
            "📧 support@nicomarket.fj"
        )
        
        await message.answer(receipt, parse_mode="Markdown", reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name))
        
        # Сохраняем информацию о заказе в историю диалога (контекст ИИ)
        user_msg = "Оформил заказ в каталоге: " + ", ".join([f"{item['title']} ({item['count']} шт.)" for item in items.values()]) + f" на сумму ${total}"
        await bot.memory.memory.add_message(message.from_user.id, "user", user_msg)
        await bot.memory.memory.add_message(message.from_user.id, "assistant", receipt)
    except Exception as e:
        logging.error(f"Ошибка парсинга данных MiniApp: {e}")
        await message.answer("⚠️ При обработке заказа произошёл сбой. Пожалуйста, повторите попытку или обратитесь к менеджеру: +679 764-2658.", reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name))


@router.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    # Rate limiting через объект memory
    if not await bot.memory.memory.check_rate_limit(user_id, RATE_LIMIT):
        await message.answer("⏳ Я обрабатываю Ваш предыдущий запрос. Пожалуйста, подождите несколько секунд.", reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name))
        return

    # Обработка нетекстовых сообщений
    if not message.text:
        await message.answer("На данный момент я воспринимаю только текстовые сообщения. Пожалуйста, сформулируйте Ваш вопрос текстом.", reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name))
        return

    # Проверка длины сообщения
    if len(message.text) > 1000:
        await message.answer("Сообщение превышает допустимый объём. Пожалуйста, сократите запрос до 1 000 символов — это поможет мне дать точный ответ.", reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name))
        return

    # Показываем статус "печатает"
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    processing_msg = await message.answer("🔄 Анализирую запрос...")

    try:
        chat_history = await bot.memory.memory.get_history(user_id)
        
        # 2. Вызов ARQ Worker для генерации
        if arq_pool:
            history_dicts = [{"role": msg.role, "text": msg.text} for msg in chat_history]
            job = await arq_pool.enqueue_job(
                "process_question",
                user_id=user_id,
                question=message.text,
                chat_history=history_dicts,
            )
            result = await job.result(timeout=120)
            if result:
                full_answer = result["answer"]
            else:
                full_answer = ""
        else:
            # Fallback на локальную обработку если ARQ не настроен
            search_query = message.text
            if chat_history:
                # Добавляем последние реплики пользователя для сохранения контекста поиска
                context_queries = [msg.text for msg in chat_history[-4:] if msg.role == "user"]
                context_queries.append(message.text)
                search_query = " ".join(context_queries)
                
            chunks = await search(search_query, top_k=8, distance_threshold=1.5)
            if not chunks:
                logging.warning("⚠️ Ничего не найдено в базе знаний! Использую fallback.")
                fallback_answer = (
                    "К сожалению, данный вопрос выходит за пределы имеющейся у меня информации. "
                    "Рекомендую обратиться к менеджеру — он сможет предоставить исчерпывающую консультацию.\n\n"
                    "📞 +679 764-2658 (08:00–22:00)\n"
                    "📧 support@nicomarket.fj"
                )
                await processing_msg.edit_text(fallback_answer)
                await bot.memory.memory.add_message(user_id, "user", message.text)
                await bot.memory.memory.add_message(user_id, "assistant", fallback_answer)
                return
                
            # Потоковая генерация ответа
            full_answer = ""
            last_edit_time = time.time()
            async with generation_semaphore:
                async for partial_answer in generate_answer_stream(message.text, chunks, chat_history):
                    if not partial_answer:
                        continue
                        
                    full_answer = partial_answer
                    now = time.time()
                    if now - last_edit_time > 1.5:
                        try:
                            await processing_msg.edit_text(partial_answer + " ▌")
                            last_edit_time = now
                        except Exception as edit_error:
                            logging.debug(f"Пропуск обновления стриминга: {edit_error}")

        from rag.guardrails import validate_response

        # Финальный текст и валидация
        if full_answer:
            validated_answer, warnings = validate_response(full_answer)
            
            if warnings:
                logging.warning(f"⚠️ Guardrails сработали для user {user_id}: {warnings}")
                if len(warnings) >= 3:
                    validated_answer = (
                        "Прошу прощения — в данном случае я не могу гарантировать полную точность ответа. "
                        "Чтобы Вы получили достоверную информацию, рекомендую связаться с менеджером.\n\n"
                        "📞 +679 764-2658\n📧 support@nicomarket.fj"
                    )
            
            await processing_msg.edit_text(validated_answer)
            
            # Лог для аудита галлюцинаций
            logging.info(
                f"📊 AUDIT | user={user_id} | "
                f"query='{message.text[:80]}' | "
                f"guardrail_warnings={len(warnings)} | "
                f"answer_len={len(validated_answer)}"
            )
            
            # Сохраняем диалог в память
            await bot.memory.memory.add_message(user_id, "user", message.text)
            await bot.memory.memory.add_message(user_id, "assistant", validated_answer)
        else:
            await processing_msg.edit_text(
                "К сожалению, мне не удалось сформировать корректный ответ. Попробуйте переформулировать запрос или свяжитесь с менеджером: +679 764-2658."
            )

    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        await processing_msg.edit_text(
            "⚠️ Произошёл технический сбой. Пожалуйста, повторите запрос чуть позже. Если ситуация повторится — свяжитесь с поддержкой: +679 764-2658."
        )
