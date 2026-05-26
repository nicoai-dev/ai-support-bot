"""Тесты для in-memory хранилища диалогов."""
import pytest
import time
from bot.memory import MemoryStorage


@pytest.fixture
def storage():
    """Создать чистое хранилище для каждого теста."""
    return MemoryStorage(max_messages=4, session_ttl=5)


@pytest.mark.asyncio
class TestMemoryStorage:
    
    async def test_add_and_get_message(self, storage):
        """Добавление и получение сообщения."""
        await storage.add_message(1, "user", "Привет!")
        history = await storage.get_history(1)
        assert len(history) == 1
        assert history[0].text == "Привет!"
        assert history[0].role == "user"
    
    async def test_max_messages_limit(self, storage):
        """История не превышает max_messages."""
        for i in range(10):
            await storage.add_message(1, "user", f"Сообщение {i}")
        history = await storage.get_history(1)
        assert len(history) == 4  # max_messages=4
        assert history[0].text == "Сообщение 6"  # Старые удалены
    
    async def test_rate_limit(self, storage):
        """Rate limit блокирует слишком частые сообщения."""
        assert await storage.check_rate_limit(1, 1.0) is True
        assert await storage.check_rate_limit(1, 1.0) is False  # Слишком рано
    
    async def test_clear_user(self, storage):
        """Очистка истории пользователя."""
        await storage.add_message(1, "user", "Привет!")
        await storage.clear(1)
        history = await storage.get_history(1)
        assert len(history) == 0
    
    async def test_session_ttl_expiry(self, storage):
        """Сессия истекает после TTL."""
        await storage.add_message(1, "user", "Привет!")
        # Симулируем протухание (подменяем last_active)
        storage._sessions[1].last_active = time.time() - 10  # TTL=5, прошло 10 сек
        history = await storage.get_history(1)
        assert len(history) == 0  # Семмия протухла
    
    async def test_cleanup_expired(self, storage):
        """cleanup_expired удаляет протухшие сессии."""
        await storage.add_message(1, "user", "Привет!")
        await storage.add_message(2, "user", "Привет от другого!")
        
        # Протухаем только user 1
        storage._sessions[1].last_active = time.time() - 10
        
        count = await storage.cleanup_expired()
        assert count == 1  # Удалён 1 пользователь
        
        # User 2 всё ещё доступен
        history = await storage.get_history(2)
        assert len(history) == 1
    
    async def test_different_users_isolated(self, storage):
        """Сообщения разных пользователей не смешиваются."""
        await storage.add_message(1, "user", "Сообщение от user 1")
        await storage.add_message(2, "user", "Сообщение от user 2")
        
        h1 = await storage.get_history(1)
        h2 = await storage.get_history(2)
        
        assert len(h1) == 1
        assert h1[0].text == "Сообщение от user 1"
        assert len(h2) == 1
        assert h2[0].text == "Сообщение от user 2"
