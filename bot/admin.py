"""Admin-команды бота. Доступны только пользователям из settings.ADMIN_USER_IDS."""
import logging
import time
from aiogram import Router, types, F
from aiogram.filters import Command
from config import settings

admin_router = Router()


def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором."""
    return user_id in settings.ADMIN_USER_IDS


@admin_router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Показать список admin-команд."""
    if not is_admin(message.from_user.id):
        return  # Молча игнорируем
    
    help_text = (
        "🔧 **Панель администратора**\n\n"
        "📊 /stats — Статистика бота\n"
        "📦 /orders — Последние заказы\n"
        "🔄 /reload\\_kb — Перезагрузить базу знаний\n"
        "🏥 /health\\_check — Состояние компонентов\n"
        "📋 /sessions — Активные сессии\n"
    )
    await message.answer(help_text, parse_mode="Markdown")


@admin_router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Показать статистику бота."""
    if not is_admin(message.from_user.id):
        return
    
    try:
        from bot.orders import order_storage
        order_stats = await order_storage.get_stats()
        
        text = (
            "📊 **Статистика бота**\n\n"
            f"📦 **Заказы:**\n"
            f"  • Всего: {order_stats['total_orders']}\n"
            f"  • Выручка: ${order_stats['total_revenue']:.2f}\n"
        )
        
        if order_stats.get("by_status"):
            text += "\n  **По статусам:**\n"
            for status, count in order_stats["by_status"].items():
                emoji = {"new": "🆕", "confirmed": "✅", "delivered": "📬", "cancelled": "❌"}.get(status, "❓")
                text += f"    {emoji} {status}: {count}\n"
        
        # Попытка получить метрики Prometheus
        try:
            from bot.metrics import messages_total, llm_requests_total, active_sessions
            text += (
                f"\n💬 **Сессии:**\n"
                f"  • Активные: {active_sessions._value.get()}\n"
            )
        except Exception:
            pass
        
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики: {e}")
        logging.error(f"Ошибка /stats: {e}")


@admin_router.message(Command("orders"))
async def cmd_orders(message: types.Message):
    """Показать последние заказы."""
    if not is_admin(message.from_user.id):
        return
    
    try:
        from bot.orders import order_storage
        
        # Получаем последние заказы (для PG — через прямой запрос)
        if order_storage._pg_pool:
            async with order_storage._pg_pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT order_id, user_id, user_name, total, status, created_at "
                    "FROM orders ORDER BY created_at DESC LIMIT 10"
                )
                if not rows:
                    await message.answer("📦 Заказов пока нет.")
                    return
                
                text = "📦 **Последние 10 заказов:**\n\n"
                for row in rows:
                    emoji = {"new": "🆕", "confirmed": "✅", "delivered": "📬", "cancelled": "❌"}.get(row["status"], "❓")
                    text += (
                        f"{emoji} `{row['order_id']}` — ${float(row['total']):.0f} "
                        f"| {row['user_name']} (ID:{row['user_id']})\n"
                    )
                await message.answer(text, parse_mode="Markdown")
        else:
            orders = list(order_storage._orders.values())[-10:]
            if not orders:
                await message.answer("📦 Заказов пока нет.")
                return
            
            text = "📦 **Последние заказы (in-memory):**\n\n"
            for o in reversed(orders):
                text += f"🆕 `{o.order_id}` — ${o.total:.0f} | {o.user_name}\n"
            await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@admin_router.message(Command("reload_kb"))
async def cmd_reload_kb(message: types.Message):
    """Горячая перезагрузка базы знаний."""
    if not is_admin(message.from_user.id):
        return
    
    try:
        await message.answer("🔄 Перезагружаю базу знаний...")
        from rag.retriever import reload_index
        count = await reload_index()
        await message.answer(f"✅ База знаний перезагружена! Чанков: {count}")
    except Exception as e:
        await message.answer(f"❌ Ошибка перезагрузки: {e}")
        logging.error(f"Ошибка /reload_kb: {e}")


@admin_router.message(Command("health_check"))
async def cmd_health_check(message: types.Message):
    """Проверить состояние компонентов."""
    if not is_admin(message.from_user.id):
        return
    
    try:
        from rag.chain import check_ollama_health
        
        llm_ok = await check_ollama_health()
        
        # Проверка Redis
        redis_ok = False
        try:
            from bot.cache import redis_cache
            await redis_cache.set("health_check", "ok", ttl=5)
            redis_ok = True
        except Exception:
            pass
        
        text = (
            "🏥 **Состояние компонентов:**\n\n"
            f"{'✅' if llm_ok else '❌'} LLM Provider ({settings.LLM_PROVIDER})\n"
            f"{'✅' if redis_ok else '❌'} Redis\n"
            f"🔧 Окружение: {settings.ENV}\n"
            f"📝 Лог-уровень: {settings.LOG_LEVEL}\n"
        )
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@admin_router.message(Command("sessions"))
async def cmd_sessions(message: types.Message):
    """Показать активные сессии."""
    if not is_admin(message.from_user.id):
        return
    
    try:
        from bot.memory import memory
        
        if hasattr(memory, '_sessions'):
            active = len(memory._sessions)
            text = f"📋 **Активные сессии:** {active}\n"
            
            if active > 0:
                text += "\n"
                for uid, session in list(memory._sessions.items())[:20]:
                    msg_count = len(session.messages)
                    elapsed = int(time.time() - session.last_active)
                    text += f"  • User `{uid}`: {msg_count} сообщ., {elapsed}с назад\n"
                
                if active > 20:
                    text += f"\n  _...и ещё {active - 20} сессий_"
        else:
            text = "📋 Хранилище не поддерживает просмотр сессий (PostgreSQL)"
        
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
