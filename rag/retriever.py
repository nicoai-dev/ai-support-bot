import asyncio
import chromadb
import logging
from sentence_transformers import SentenceTransformer
from rag.loader import load_documents, split_into_chunks
from config import KNOWLEDGE_BASE_DIR, CHROMA_DB_DIR


# Кеширование модели и клиента
_model = None
_client = None

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
    logging.info(f"✅ База знаний успешно обновлена! Проиндексировано чанков: {len(chunks)}")


async def search(query: str, top_k: int = 5, distance_threshold: float = 0.8) -> list[str]:
    """Найти top_k самых релевантных чанков по запросу с фильтрацией по дистанции."""
    model = get_embedding_model()
    # Нормализуем и здесь
    query_embedding = await asyncio.to_thread(model.encode, [query], normalize_embeddings=True)
    query_embedding = query_embedding.tolist()

    client = get_chroma_client()
    try:
        collection = client.get_collection("knowledge_base")
    except Exception:
        logging.warning("⚠️ Индекс не найден. Пересоздаем...")
        await build_index()
        collection = client.get_collection("knowledge_base")

    results = await asyncio.to_thread(
        collection.query,
        query_embeddings=query_embedding,
        n_results=top_k,
    )
    
    if not results["documents"] or not results["documents"][0]:
        return []

    # Фильтрация по дистанции
    filtered_chunks = []
    if results["documents"] and results["distances"] and results["metadatas"]:
        for doc, dist, meta in zip(results["documents"][0], results["distances"][0], results["metadatas"][0]):
            source = meta.get("source", "unknown")
            logging.info(f"🔍 Найден чанк [{source}] (dist: {dist:.4f}): {doc[:60]}...")
            
            if dist < distance_threshold:
                filtered_chunks.append(doc)
            else:
                logging.warning(f"⚠️ Чанк из {source} отброшен (dist {dist:.4f} > {distance_threshold})")
            
    return filtered_chunks
