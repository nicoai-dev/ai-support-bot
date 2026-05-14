import chromadb
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


def build_index():
    """Загрузить документы, создать эмбеддинги, сохранить в ChromaDB."""
    docs = load_documents(KNOWLEDGE_BASE_DIR)
    if not docs:
        print("Warning: No documents in knowledge base!")
        return

    chunks = split_into_chunks(docs)
    model = get_embedding_model()
    embeddings = model.encode(chunks).tolist()

    client = get_chroma_client()

    # Удалить старую коллекцию если есть
    try:
        client.delete_collection("knowledge_base")
    except Exception:
        pass

    collection = client.create_collection("knowledge_base")
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=[f"chunk_{i}" for i in range(len(chunks))],
    )
    print(f"Indexed {len(chunks)} chunks")


def search(query: str, top_k: int = 5, distance_threshold: float = 2.0) -> list[str]:
    """Найти top_k самых релевантных чанков по запросу с фильтрацией по дистанции."""
    model = get_embedding_model()
    query_embedding = model.encode([query]).tolist()

    client = get_chroma_client()
    try:
        collection = client.get_collection("knowledge_base")
    except Exception:
        print("Warning: Index not found. Rebuilding...")
        build_index()
        collection = client.get_collection("knowledge_base")

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
    )
    
    if not results["documents"] or not results["documents"][0]:
        return []

    # Фильтрация по дистанции (в ChromaDB чем меньше дистанция, тем выше схожесть)
    filtered_chunks = []
    for doc, dist in zip(results["documents"][0], results["distances"][0]):
        if dist < distance_threshold:
            filtered_chunks.append(doc)
            
    return filtered_chunks
