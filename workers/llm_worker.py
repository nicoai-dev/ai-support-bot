import logging
import arq
from arq.connections import RedisSettings
from rag.chain import generate_answer_collect
from rag.guardrails import validate_response
from rag.retriever import search, load_chunks_to_memory
from config import settings, REDIS_URL


async def startup(ctx):
    """Загружаем чанки и BM25-индекс в память воркера при старте."""
    logging.info("🚀 arq-worker: загружаем BM25-индекс в память...")
    await load_chunks_to_memory()
    logging.info("✅ arq-worker: BM25-индекс готов.")


def _build_search_query(question: str, chat_history: list) -> str:
    """Построить расширенный запрос для поиска с учётом истории диалога.
    
    Общая логика, используемая и в handlers.py, и в worker — 
    вынесена сюда, чтобы не дублировать.
    """
    if not chat_history:
        return question
    context_queries = [
        msg.get("text", "") 
        for msg in chat_history[-4:] 
        if msg.get("role") == "user"
    ]
    context_queries.append(question)
    return " ".join(context_queries)


async def process_question(ctx, user_id: int, question: str, chat_history: list):
    """ARQ task: поиск + генерация ответа + guardrails."""
    
    search_query = _build_search_query(question, chat_history)
    chunks = await search(search_query, top_k=settings.RAG_TOP_K, distance_threshold=settings.RAG_DISTANCE_THRESHOLD)
    
    # Генерация ответа через LLM
    answer = await generate_answer_collect(question, chunks, chat_history)
    
    # КРИТИЧНО: Пропускаем через guardrails (раньше этого не было!)
    validated_answer, warnings = validate_response(answer)
    
    if warnings:
        logging.warning(f"⚠️ Guardrails сработали для user {user_id} (ARQ): {warnings}")
        if len(warnings) >= 3:
            validated_answer = (
                f"Прошу прощения — в данном случае я не могу гарантировать полную точность ответа. "
                f"Чтобы Вы получили достоверную информацию, рекомендую связаться с менеджером.\n\n"
                f"📞 {settings.SUPPORT_PHONE}\n📧 {settings.SUPPORT_EMAIL}"
            )
    
    # Аудит-лог
    logging.info(
        f"📊 AUDIT (ARQ) | user={user_id} | "
        f"query='{question[:80]}' | "
        f"guardrail_warnings={len(warnings)} | "
        f"answer_len={len(validated_answer)}"
    )
    
    return {"user_id": user_id, "answer": validated_answer}


class WorkerSettings:
    on_startup = startup
    functions = [process_question]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    max_jobs = 1
    job_timeout = 300
    health_check_interval = 30
