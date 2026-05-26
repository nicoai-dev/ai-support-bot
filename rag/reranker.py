from sentence_transformers import CrossEncoder
import asyncio
import logging

_reranker: CrossEncoder | None = None

def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        # Мультиязычная модель для русского
        _reranker = CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    return _reranker

async def rerank(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """Переранжировать чанки cross-encoder'ом."""
    if not chunks:
        return []
    
    reranker = get_reranker()
    pairs = [(query, c["text"]) for c in chunks]
    
    scores = await asyncio.to_thread(reranker.predict, pairs)
    
    scored = list(zip(chunks, scores))
    scored.sort(key=lambda x: x[1], reverse=True)
    
    for chunk, score in scored[:top_k]:
        logging.debug(f"Reranker score: {score:.4f} | Chunk: {chunk['source']}")
    return [chunk for chunk, score in scored[:top_k] if score > -6.0]
