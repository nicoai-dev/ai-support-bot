import asyncio
import chromadb
import logging
from sentence_transformers import SentenceTransformer
from rag.loader import load_documents, split_into_chunks
from config import KNOWLEDGE_BASE_DIR, CHROMA_DB_DIR
from rag.bm25_index import BM25Index
from collections import defaultdict

# Кеширование модели и клиента
_model = None
_client = None
_bm25_index: BM25Index | None = None
_all_chunks: list[dict] = []

def get_embedding_model():
    global _model
    if _model is None:
        # Мультиязычная модель для лучшего поиска на русском языке
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model

def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    return _client


async def build_index():
    """Загрузить документы, создать эмбеддинги, сохранить в ChromaDB с метаданными."""
    docs = await asyncio.to_thread(load_documents, KNOWLEDGE_BASE_DIR)
    if not docs:
        logging.warning("⚠️ В базе знаний нет документов для индексации!")
        return

    chunks = await asyncio.to_thread(split_into_chunks, docs)
    model = get_embedding_model()
    
    texts = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"]} for c in chunks]
    
    # Добавляем нормализацию для стабильных дистанций
    embeddings = await asyncio.to_thread(model.encode, texts, normalize_embeddings=True)
    embeddings = embeddings.tolist()

    client = get_chroma_client()

    def _sync_index_update():
        # Удалить старую коллекцию если есть
        try:
            client.delete_collection("knowledge_base")
        except Exception:
            pass

        # Создаем коллекцию с косинусным расстоянием
        collection = client.create_collection(
            name="knowledge_base", 
            metadata={"hnsw:space": "cosine"}
        )
        
        collection.add(
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=[f"chunk_{i}" for i in range(len(chunks))],
        )

    await asyncio.to_thread(_sync_index_update)
    
    global _all_chunks, _bm25_index
    _all_chunks = chunks
    _bm25_index = BM25Index()
    _bm25_index.index(chunks)
    
    logging.info(f"✅ База знаний успешно обновлена! Проиндексировано чанков: {len(chunks)} (в т.ч. BM25)")

async def load_chunks_to_memory():
    """Загрузить чанки и BM25 индекс в память (без обновления ChromaDB)."""
    global _all_chunks, _bm25_index
    if _all_chunks:
        return
    docs = await asyncio.to_thread(load_documents, KNOWLEDGE_BASE_DIR)
    chunks = await asyncio.to_thread(split_into_chunks, docs)
    _all_chunks = chunks
    _bm25_index = BM25Index()
    _bm25_index.index(chunks)
    logging.info(f"💾 Загружено в память чанков: {len(chunks)}")

def _reciprocal_rank_fusion(
    vector_results: list[tuple[int, float]],
    bm25_results: list[tuple[int, float]],
    k: int = 60
) -> list[int]:
    """RRF: объединяет два ранжированных списка."""
    scores = defaultdict(float)
    for rank, (doc_id, _) in enumerate(vector_results):
        scores[doc_id] += 1.0 / (k + rank + 1)
    for rank, (doc_id, _) in enumerate(bm25_results):
        scores[doc_id] += 1.0 / (k + rank + 1)
    return [doc_id for doc_id, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)]


async def search(query: str, top_k: int = 8, distance_threshold: float = 1.5) -> list[dict]:
    """Найти top_k самых релевантных чанков по запросу (Hybrid: Vector + BM25)."""
    model = get_embedding_model()
    # Нормализуем и здесь
    query_embedding = await asyncio.to_thread(model.encode, [query], normalize_embeddings=True)
    query_embedding = query_embedding.tolist()

    if not _all_chunks:
        await load_chunks_to_memory()

    client = get_chroma_client()
    try:
        collection = client.get_collection("knowledge_base")
    except Exception:
        logging.warning("⚠️ Индекс не найден. Пересоздаем...")
        await build_index()
        collection = client.get_collection("knowledge_base")

    # Vector search — берём текст и метаданные прямо из ответа ChromaDB,
    # чтобы не зависеть от совпадения индексов с _all_chunks в памяти.
    n_results = min(20, max(1, len(_all_chunks) if _all_chunks else 20))
    results = await asyncio.to_thread(
        collection.query,
        query_embeddings=query_embedding,
        n_results=n_results,
    )

    # Строим словарь id -> (text, source, dist) из ответа ChromaDB
    chroma_map: dict[int, dict] = {}
    vector_results: list[tuple[int, float]] = []
    if results["ids"] and results["documents"] and results["distances"]:
        for doc_id_str, text, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if dist < distance_threshold:
                idx = int(doc_id_str.split("_")[1])
                chroma_map[idx] = {
                    "text": text,
                    "source": meta.get("source", ""),
                }
                vector_results.append((idx, dist))

    # BM25 search (требует _all_chunks в памяти)
    bm25_results = _bm25_index.search(query, top_k=20) if _bm25_index else []

    # Fusion
    fused_ids = _reciprocal_rank_fusion(vector_results, bm25_results)

    # Собрать кандидатов для reranking.
    # Текст берём из chroma_map (вектор-кандидаты) или из _all_chunks (BM25-only кандидаты).
    candidates = []
    for idx in fused_ids[:20]:
        if idx in chroma_map:
            candidates.append({"text": chroma_map[idx]["text"], "source": chroma_map[idx]["source"], "distance": 0.0})
        elif _all_chunks and 0 <= idx < len(_all_chunks):
            chunk = _all_chunks[idx]
            candidates.append({"text": chunk["text"], "source": chunk["source"], "distance": 0.0})
        else:
            logging.warning(f"⚠️ Пропущен idx={idx}: нет ни в chroma_map, ни в _all_chunks (len={len(_all_chunks)})")
        
    from rag.reranker import rerank
    reranked = await rerank(query, candidates, top_k=top_k)
    
    for chunk in reranked:
        logging.info(f"🔍 Найден чанк [{chunk['source']}] (Hybrid + Rerank): {chunk['text'][:60]}...")
            
    return reranked


async def reload_index():
    """Горячая перезагрузка базы знаний без рестарта бота.
    
    Используется admin-командой /reload_kb.
    Безопасно: новый индекс строится до замены старого.
    """
    global _all_chunks, _bm25_index
    
    logging.info("🔄 Горячая перезагрузка базы знаний...")
    
    # Загружаем и индексируем новые документы
    docs = await asyncio.to_thread(load_documents, KNOWLEDGE_BASE_DIR)
    if not docs:
        logging.warning("⚠️ Нет документов для перезагрузки!")
        return 0
    
    chunks = await asyncio.to_thread(split_into_chunks, docs)
    model = get_embedding_model()
    
    texts = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"]} for c in chunks]
    embeddings = await asyncio.to_thread(model.encode, texts, normalize_embeddings=True)
    embeddings = embeddings.tolist()
    
    client = get_chroma_client()
    
    def _sync_reindex():
        try:
            client.delete_collection("knowledge_base")
        except Exception:
            pass
        collection = client.create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"},
        )
        collection.add(
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=[f"chunk_{i}" for i in range(len(chunks))],
        )
    
    await asyncio.to_thread(_sync_reindex)
    
    # Атомарно обновляем глобальные переменные
    new_bm25 = BM25Index()
    new_bm25.index(chunks)
    _all_chunks = chunks
    _bm25_index = new_bm25
    
    logging.info(f"✅ База знаний перезагружена! Чанков: {len(chunks)}")
    return len(chunks)
