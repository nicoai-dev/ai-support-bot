import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.storage import MessageRecord
from rag.retriever import search
from rag.chain import _build_search_query
import time

async def main():
    print("\n--- Тест 2.2.1: Гибридный поиск (Релевантный запрос) ---")
    res1 = await search("Какие смартфоны у вас есть?")
    print(f"Найдено чанков: {len(res1)}")
    if res1:
        print(f"Top 1: {res1[0]['text'][:50]}... (score: {res1[0].get('score', 0)})")

    print("\n--- Тест 2.2.2: Гибридный поиск (Опечатки) ---")
    res2 = await search("какии smartfonы продаёте?")
    print(f"Найдено чанков: {len(res2)}")

    print("\n--- Тест 2.2.3: Гибридный поиск (Нерелевантный запрос) ---")
    res3 = await search("рецепт борща")
    print(f"Найдено чанков: {len(res3)}")

    print("\n--- Тест 2.3.1: Расширение запроса (Query Expansion) ---")
    t = time.time()
    history = [
        MessageRecord(user_id=1, role="user", text="Какие ноутбуки есть?", timestamp=t),
        MessageRecord(user_id=1, role="assistant", text="У нас есть Macbook и Asus.", timestamp=t),
        MessageRecord(user_id=1, role="user", text="А сколько он стоит?", timestamp=t)
    ]
    expanded_query = await _build_search_query("А сколько он стоит?", history)
    print(f"Оригинал: 'А сколько он стоит?' -> Расширенный: '{expanded_query}'")

if __name__ == "__main__":
    asyncio.run(main())
