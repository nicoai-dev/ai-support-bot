import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

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
                        "⚠️ Произошла техническая ошибка при обработке вашего запроса.\n"
                        "Мы уже получили уведомление и работаем над исправлением. "
                        "Попробуйте повторить запрос позже."
                    )
                except Exception as send_err:
                    logging.error(f"Не удалось отправить уведомление об ошибке: {send_err}")
            
            return None
