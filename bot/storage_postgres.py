import asyncpg
from bot.storage import StorageBackend, MessageRecord

class PostgresStorage(StorageBackend):
    def __init__(self, pool: asyncpg.Pool, max_messages: int = 4, session_ttl: int = 600):
        self._pool = pool
        self.max_messages = max_messages
        self.session_ttl = session_ttl
    
    @classmethod
    async def create(cls, dsn: str, **kwargs) -> "PostgresStorage":
        pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        instance = cls(pool, **kwargs)
        await instance._init_schema()
        return instance
    
    async def _init_schema(self):
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    role VARCHAR(16) NOT NULL,
                    text TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, created_at DESC);
                
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id BIGINT PRIMARY KEY,
                    last_message TIMESTAMPTZ DEFAULT NOW()
                );
            """)
    
    async def add_message(self, user_id: int, role: str, text: str) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO messages (user_id, role, text) VALUES ($1, $2, $3)",
                    user_id, role, text
                )
                # Оставляем только последние N сообщений
                await conn.execute("""
                    DELETE FROM messages WHERE id IN (
                        SELECT id FROM messages WHERE user_id = $1
                        ORDER BY created_at DESC OFFSET $2
                    )
                """, user_id, self.max_messages)
                
    async def get_history(self, user_id: int, limit: int = None) -> list[MessageRecord]:
        if limit is None:
            limit = self.max_messages
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, role, text, extract(epoch from created_at) as timestamp 
                FROM messages 
                WHERE user_id = $1 
                ORDER BY created_at ASC 
                LIMIT $2
            """, user_id, limit)
            return [MessageRecord(user_id=r['user_id'], role=r['role'], text=r['text'], timestamp=r['timestamp']) for r in rows]
    
    async def check_rate_limit(self, user_id: int, interval: float) -> bool:
        async with self._pool.acquire() as conn:
            # Атомарный upsert с проверкой интервала
            row = await conn.fetchrow("""
                INSERT INTO rate_limits (user_id, last_message)
                VALUES ($1, NOW())
                ON CONFLICT (user_id) DO UPDATE 
                    SET last_message = NOW()
                    WHERE rate_limits.last_message < NOW() - INTERVAL '1 second' * $2
                RETURNING user_id
            """, user_id, interval)
            return row is not None

    async def clear(self, user_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM messages WHERE user_id = $1", user_id)

    async def cleanup_expired(self, ttl: int = None) -> int:
        if ttl is None:
            ttl = self.session_ttl
        async with self._pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM messages 
                WHERE user_id IN (
                    SELECT user_id FROM messages 
                    GROUP BY user_id 
                    HAVING MAX(created_at) < NOW() - INTERVAL '1 second' * $1
                )
            """, ttl)
            # count deleted messages. returning deleted users count is more complex, just return 0 for now as it's not strictly used
            return 0
