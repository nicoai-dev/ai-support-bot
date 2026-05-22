import time
from dataclasses import dataclass, field
from config import MEMORY_MAX_MESSAGES, MEMORY_SESSION_TTL
from bot.storage import StorageBackend, MessageRecord

@dataclass
class Session:
    messages: list[MessageRecord] = field(default_factory=list)
    last_active: float = 0.0

class MemoryStorage(StorageBackend):
    """Хранит историю диалогов и таймауты пользователей с автоочисткой (in-memory)."""
    
    def __init__(self, max_messages: int = MEMORY_MAX_MESSAGES, session_ttl: int = MEMORY_SESSION_TTL):
        self._sessions: dict[int, Session] = {}
        self._user_timeouts: dict[int, float] = {}
        self.max_messages = max_messages
        self.session_ttl = session_ttl
    
    async def add_message(self, user_id: int, role: str, text: str) -> None:
        """Добавить сообщение в историю."""
        now = time.time()
        session = self._get_or_create(user_id, now)
        session.messages.append(MessageRecord(user_id=user_id, role=role, text=text, timestamp=now))
        session.last_active = now
        
        if len(session.messages) > self.max_messages:
            session.messages = session.messages[-self.max_messages:]
    
    async def get_history(self, user_id: int, limit: int = None) -> list[MessageRecord]:
        """Получить историю диалога."""
        if limit is None:
            limit = self.max_messages
        session = self._sessions.get(user_id)
        if not session:
            return []
        if time.time() - session.last_active > self.session_ttl:
            del self._sessions[user_id]
            return []
        return session.messages[-limit:] if limit else session.messages
    
    async def check_rate_limit(self, user_id: int, interval: float) -> bool:
        """Проверить, не слишком ли часто пишет пользователь."""
        now = time.time()
        if user_id in self._user_timeouts:
            if now - self._user_timeouts[user_id] < interval:
                return False
        self._user_timeouts[user_id] = now
        return True

    async def clear(self, user_id: int) -> None:
        """Сбросить историю пользователя."""
        self._sessions.pop(user_id, None)
    
    async def cleanup_expired(self, ttl: int = None) -> int:
        """Удалить истёкшие сессии и старые записи в таймаутах. Возвращает количество удаленных."""
        if ttl is None:
            ttl = self.session_ttl
        now = time.time()
        
        # Чистка истории
        expired_sessions = [
            uid for uid, s in self._sessions.items()
            if now - s.last_active > ttl
        ]
        for uid in expired_sessions:
            del self._sessions[uid]
            
        # Чистка таймаутов (удаляем тех, кто не писал больше часа)
        expired_timeouts = [
            uid for uid, last_time in self._user_timeouts.items()
            if now - last_time > 3600
        ]
        for uid in expired_timeouts:
            del self._user_timeouts[uid]
            
        return len(expired_sessions)
    
    def _get_or_create(self, user_id: int, now: float) -> Session:
        session = self._sessions.get(user_id)
        if session and (now - session.last_active > self.session_ttl):
            session = None
        if not session:
            session = Session(last_active=now)
            self._sessions[user_id] = session
        return session
from config import STORAGE_BACKEND, DATABASE_URL

# Глобальный экземпляр для совместимости
memory: StorageBackend

if STORAGE_BACKEND == "postgres":
    # Для postgres мы должны инициализировать пул асинхронно.
    # Создадим временную in-memory реализацию, пока не вызовем init_postgres_memory
    from bot.storage_postgres import PostgresStorage
    memory = MemoryStorage()
    
    async def init_postgres_memory():
        global memory
        if STORAGE_BACKEND == "postgres":
            memory = await PostgresStorage.create(DATABASE_URL)
else:
    memory = MemoryStorage()
