import time
from dataclasses import dataclass, field
from config import MEMORY_MAX_MESSAGES, MEMORY_SESSION_TTL

@dataclass
class Message:
    role: str         # "user" или "assistant"
    text: str
    timestamp: float

@dataclass
class Session:
    messages: list[Message] = field(default_factory=list)
    last_active: float = 0.0

class ConversationMemory:
    """Хранит историю диалогов и таймауты пользователей с автоочисткой."""
    
    def __init__(self, max_messages: int = MEMORY_MAX_MESSAGES, session_ttl: int = MEMORY_SESSION_TTL):
        self._sessions: dict[int, Session] = {}
        self._user_timeouts: dict[int, float] = {}
        self.max_messages = max_messages
        self.session_ttl = session_ttl
    
    def add_message(self, user_id: int, role: str, text: str):
        """Добавить сообщение в историю."""
        now = time.time()
        session = self._get_or_create(user_id, now)
        session.messages.append(Message(role=role, text=text, timestamp=now))
        session.last_active = now
        
        if len(session.messages) > self.max_messages:
            session.messages = session.messages[-self.max_messages:]
    
    def get_history(self, user_id: int) -> list[Message]:
        """Получить историю диалога."""
        session = self._sessions.get(user_id)
        if not session:
            return []
        if time.time() - session.last_active > self.session_ttl:
            del self._sessions[user_id]
            return []
        return session.messages
    
    def check_rate_limit(self, user_id: int, rate_limit: float) -> bool:
        """Проверить, не слишком ли часто пишет пользователь."""
        now = time.time()
        if user_id in self._user_timeouts:
            if now - self._user_timeouts[user_id] < rate_limit:
                return False
        self._user_timeouts[user_id] = now
        return True

    def clear(self, user_id: int):
        """Сбросить историю пользователя."""
        self._sessions.pop(user_id, None)
    
    def cleanup_expired(self):
        """Удалить истёкшие сессии и старые записи в таймаутах."""
        now = time.time()
        
        # Чистка истории
        expired_sessions = [
            uid for uid, s in self._sessions.items()
            if now - s.last_active > self.session_ttl
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
    
    def _get_or_create(self, user_id: int, now: float) -> Session:
        session = self._sessions.get(user_id)
        if session and (now - session.last_active > self.session_ttl):
            session = None
        if not session:
            session = Session(last_active=now)
            self._sessions[user_id] = session
        return session

# Глобальный экземпляр
memory = ConversationMemory()
