from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class MessageRecord:
    user_id: int
    role: str
    text: str
    timestamp: float

class StorageBackend(ABC):
    @abstractmethod
    async def add_message(self, user_id: int, role: str, text: str) -> None: ...
    
    @abstractmethod
    async def get_history(self, user_id: int, limit: int = 4) -> list[MessageRecord]: ...
    
    @abstractmethod
    async def check_rate_limit(self, user_id: int, interval: float) -> bool: ...
    
    @abstractmethod
    async def clear(self, user_id: int) -> None: ...
    
    @abstractmethod
    async def cleanup_expired(self, ttl: int) -> int: ...
