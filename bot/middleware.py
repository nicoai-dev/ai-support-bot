import uuid
import time
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from typing import Any, Callable, Dict, Awaitable

class RequestContextMiddleware(BaseMiddleware):
    """Middleware для добавления correlation ID к каждому запросу.
    
    Позволяет отслеживать весь путь обработки сообщения в логах.
    """
    
    async def __call__(self, handler, event, data):
        # Генерируем уникальный request ID
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Добавляем в data для доступа из хендлеров
        data["request_id"] = request_id
        
        user_id = None
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id
        
        logging.info(
            f"[{request_id}] ← Входящее сообщение | user={user_id} | type={type(event).__name__}"
        )
        
        try:
            result = await handler(event, data)
            elapsed = time.time() - start_time
            logging.info(
                f"[{request_id}] → Обработано за {elapsed:.2f}s | user={user_id}"
            )
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logging.error(
                f"[{request_id}] ✗ Ошибка за {elapsed:.2f}s | user={user_id} | error={e}"
            )
            raise

class ErrorHandlingMiddleware(BaseMiddleware):
    """
    Middleware для глобального отлова ошибок во время обработки сообщений.
    Логирует ошибку и отправляет пользователю вежливое уведомление.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logging.error(f"❌ Критическая ошибка при обработке {type(event).__name__}: {e}", exc_info=True)
            
            # Если это сообщение, отправляем уведомление пользователю
            if isinstance(event, Message):
                try:
                    await event.answer(
                        "⚠️ Произошёл технический сбой при обработке Вашего запроса.\n"
                        "Информация об инциденте уже зафиксирована. "
                        "Пожалуйста, повторите запрос через некоторое время."
                    )
                except Exception as send_err:
                    logging.error(f"Не удалось отправить уведомление об ошибке: {send_err}")
            
            return None
