"""Модуль обработки и хранения заказов."""
import logging
import json
import time
from dataclasses import dataclass, field
from typing import Optional
from config import settings


@dataclass
class Order:
    """Структура заказа."""
    order_id: str
    user_id: int
    user_name: str
    items: dict  # {product_id: {title, price, count}}
    total: float
    status: str = "new"  # new → confirmed → delivered → cancelled
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "items": self.items,
            "total": self.total,
            "status": self.status,
            "created_at": self.created_at,
        }


class OrderStorage:
    """Хранилище заказов.
    
    Для dev: in-memory dict.
    Для prod: PostgreSQL (через тот же пул, что и storage_postgres).
    """
    
    def __init__(self):
        self._orders: dict[str, Order] = {}
        self._counter: int = 0
        self._pg_pool = None
    
    async def init_postgres(self, pool) -> None:
        """Инициализировать PostgreSQL-хранилище заказов."""
        self._pg_pool = pool
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    user_name TEXT NOT NULL DEFAULT '',
                    items JSONB NOT NULL,
                    total NUMERIC(10, 2) NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)
            """)
        logging.info("✅ Таблица orders создана / проверена")
    
    def _generate_id(self) -> str:
        """Сгенерировать уникальный номер заказа."""
        self._counter += 1
        timestamp = int(time.time()) % 100000
        return f"NM-{timestamp}-{self._counter:04d}"
    
    async def create_order(self, user_id: int, user_name: str, items: dict, total: float) -> Order:
        """Создать новый заказ."""
        order_id = self._generate_id()
        order = Order(
            order_id=order_id,
            user_id=user_id,
            user_name=user_name,
            items=items,
            total=total,
        )
        
        if self._pg_pool:
            async with self._pg_pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO orders (order_id, user_id, user_name, items, total, status)
                       VALUES ($1, $2, $3, $4::jsonb, $5, $6)""",
                    order.order_id, order.user_id, order.user_name,
                    json.dumps(order.items, ensure_ascii=False),
                    order.total, order.status,
                )
        else:
            self._orders[order_id] = order
        
        logging.info(
            f"📦 Заказ создан: {order_id} | user={user_id} | total=${total:.2f} | items={len(items)}"
        )
        return order
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Получить заказ по ID."""
        if self._pg_pool:
            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM orders WHERE order_id = $1", order_id
                )
                if row:
                    return Order(
                        order_id=row["order_id"],
                        user_id=row["user_id"],
                        user_name=row["user_name"],
                        items=json.loads(row["items"]) if isinstance(row["items"], str) else row["items"],
                        total=float(row["total"]),
                        status=row["status"],
                        created_at=row["created_at"].timestamp(),
                    )
        return self._orders.get(order_id)
    
    async def get_user_orders(self, user_id: int, limit: int = 10) -> list[Order]:
        """Получить заказы пользователя."""
        if self._pg_pool:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
                    user_id, limit,
                )
                return [
                    Order(
                        order_id=row["order_id"],
                        user_id=row["user_id"],
                        user_name=row["user_name"],
                        items=json.loads(row["items"]) if isinstance(row["items"], str) else row["items"],
                        total=float(row["total"]),
                        status=row["status"],
                        created_at=row["created_at"].timestamp(),
                    )
                    for row in rows
                ]
        return [o for o in self._orders.values() if o.user_id == user_id][-limit:]
    
    async def get_stats(self) -> dict:
        """Получить статистику по заказам (для admin)."""
        if self._pg_pool:
            async with self._pg_pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM orders")
                revenue = await conn.fetchval("SELECT COALESCE(SUM(total), 0) FROM orders")
                by_status = await conn.fetch(
                    "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
                )
                return {
                    "total_orders": total,
                    "total_revenue": float(revenue),
                    "by_status": {row["status"]: row["cnt"] for row in by_status},
                }
        return {
            "total_orders": len(self._orders),
            "total_revenue": sum(o.total for o in self._orders.values()),
            "by_status": {},
        }


# Глобальный экземпляр
order_storage = OrderStorage()
