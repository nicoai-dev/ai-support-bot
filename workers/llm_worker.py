import logging
import arq
from arq.connections import RedisSettings
from rag.chain import generate_answer_collect
from rag.retriever import search, load_chunks_to_memory
from config import REDIS_URL


async def startup(ctx):
    """Загружаем чанки и BM25-индекс в память воркера при старте."""
    logging.info("🚀 arq-worker: загружаем BM25-индекс в память...")
    await load_chunks_to_memory()
    logging.info("✅ arq-worker: BM25-индекс готов.")


async def process_question(ctx, user_id: int, question: str, chat_history: list):
    """ARQ task: поиск + генерация ответа."""
    
    # Формируем расширенный запрос для векторного поиска, 
    # чтобы не терять контекст (например, если пользователь пишет "А какие есть?" 
    # после обсуждения смартфонов).
    search_query = question
    if chat_history:
        context_queries = []
        for msg in chat_history[-4:]:
            if msg.get("role") == "user":
                context_queries.append(msg.get("text", ""))
        context_queries.append(question)
        search_query = " ".join(context_queries)
        
    chunks = await search(search_query, top_k=4, distance_threshold=1.5)
    answer = await generate_answer_collect(question, chunks, chat_history)
    return {"user_id": user_id, "answer": answer}


class WorkerSettings:
    on_startup = startup
    functions = [process_question]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    max_jobs = 1
    job_timeout = 300
    health_check_interval = 30
