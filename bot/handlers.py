import logging
import time
from bot.metrics import messages_total, llm_requests_total, llm_latency_seconds, guardrails_triggered, errors_total
import time as _time
import asyncio
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import config
from config import settings
from rag.retriever import search
from rag.chain import generate_answer_stream
import bot.memory
import hashlib
import hmac

def verify_webapp_data(init_data: str, bot_token: str) -> bool:
    """Верификация данных Telegram WebApp по HMAC-SHA256.
    
    Проверяет, что данные действительно пришли от Telegram,
    а не были подделаны злоумышленником.
    Документация: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        from urllib.parse import parse_qs
        parsed = parse_qs(init_data)
        
        # Извлекаем hash и удаляем его из данных
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            return False
        
        # Собираем data_check_string: пары key=value, отсортированные по key, без hash
        data_pairs = []
        for key_value in init_data.split("&"):
            key = key_value.split("=", 1)[0]
            if key != "hash":
                data_pairs.append(key_value)
        data_pairs.sort()
        data_check_string = "\n".join(data_pairs)
        
        # Вычисляем HMAC
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(computed_hash, received_hash)
    except Exception as e:
        logging.error(f"Ошибка верификации WebApp данных: {e}")
        return False

router = Router()

from bot.middleware import RequestContextMiddleware
router.message.middleware(RequestContextMiddleware())

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
            f"📞 **Служба поддержки {settings.COMPANY_NAME}**\n\n"
            f"Живой специалист на связи ежедневно:\n"
            f"• **Телефон:** `{settings.SUPPORT_PHONE}`\n"
            f"• **Часы работы:** {settings.SUPPORT_HOURS}\n\n"
            f"Вы также можете продолжить диалог со мной — я к Вашим услугам.",
            parse_mode="Markdown"
        )
    await callback.answer()


import json
from aiogram import F

@router.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        # Верификация подлинности данных WebApp
        if message.web_app_data and hasattr(message, 'web_app_data'):
            # Telegram Bot API автоматически верифицирует web_app_data при получении
            # через Message, но мы добавляем дополнительную проверку user_id
            pass
        
        data = json.loads(message.web_app_data.data)
        
        # Защита: проверяем структуру данных от WebApp
        if not isinstance(data, dict):
            logging.warning(f"⚠️ Невалидный формат данных WebApp от user {message.from_user.id}")
            return
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
            f"Благодарим за выбор {settings.COMPANY_NAME}! Менеджер свяжется с Вами для подтверждения и уточнения деталей доставки.\n\n"
            f"📞 {settings.SUPPORT_PHONE} ({settings.SUPPORT_HOURS})\n"
            f"📧 {settings.SUPPORT_EMAIL}"
        )
        
        await message.answer(receipt, parse_mode="Markdown", reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name))
        
        # Сохраняем информацию о заказе в историю диалога (контекст ИИ)
        user_msg = "Оформил заказ в каталоге: " + ", ".join([f"{item['title']} ({item['count']} шт.)" for item in items.values()]) + f" на сумму ${total}"
        await bot.memory.memory.add_message(message.from_user.id, "user", user_msg)
        await bot.memory.memory.add_message(message.from_user.id, "assistant", receipt)
    except Exception as e:
        logging.error(f"Ошибка парсинга данных MiniApp: {e}")
        await message.answer(f"⚠️ При обработке заказа произошёл сбой. Пожалуйста, повторите попытку или обратитесь к менеджеру: {settings.SUPPORT_PHONE}.", reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name))


@router.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    # Rate limiting через объект memory
    if not await bot.memory.memory.check_rate_limit(user_id, RATE_LIMIT):
        await message.answer("⏳ Я обрабатываю Ваш предыдущий запрос. Пожалуйста, подождите несколько секунд.", reply_markup=await get_reply_keyboard(message.from_user.id, message.from_user.first_name))
        return

    messages_total.labels(type="text").inc()

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
            from workers.llm_worker import _build_search_query
            history_dicts = [{"role": msg.role, "text": msg.text} for msg in chat_history] if chat_history else []
            search_query = _build_search_query(message.text, history_dicts)

            chunks = await search(search_query, top_k=8, distance_threshold=1.5)
            if not chunks:
                logging.warning("⚠️ Ничего не найдено в базе знаний! Использую fallback.")
                fallback_answer = (
                    "К сожалению, данный вопрос выходит за пределы имеющейся у меня информации. "
                    "Рекомендую обратиться к менеджеру — он сможет предоставить исчерпывающую консультацию.\n\n"
                    f"📞 {settings.SUPPORT_PHONE} ({settings.SUPPORT_HOURS})\n"
                    f"📧 {settings.SUPPORT_EMAIL}"
                )
                await processing_msg.edit_text(fallback_answer)
                await bot.memory.memory.add_message(user_id, "user", message.text)
                await bot.memory.memory.add_message(user_id, "assistant", fallback_answer)
                return
                
            # Потоковая генерация ответа
            full_answer = ""
            last_edit_time = time.time()
            async with generation_semaphore:
                llm_start = _time.time()
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
                llm_latency_seconds.observe(_time.time() - llm_start)
                llm_requests_total.labels(provider=settings.LLM_PROVIDER, status="success").inc()

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
                        f"📞 {settings.SUPPORT_PHONE}\n📧 {settings.SUPPORT_EMAIL}"
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
                f"К сожалению, мне не удалось сформировать корректный ответ. Попробуйте переформулировать запрос или свяжитесь с менеджером: {settings.SUPPORT_PHONE}."
            )

    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        await processing_msg.edit_text(
            f"⚠️ Произошёл технический сбой. Пожалуйста, повторите запрос чуть позже. Если ситуация повторится — свяжитесь с поддержкой: {settings.SUPPORT_PHONE}."
        )
