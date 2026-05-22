import math
from collections import Counter, defaultdict
import re

class BM25Index:
    """Лёгкий BM25 индекс без внешних зависимостей."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: list[dict] = []
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.doc_lens: list[int] = []
        self.avg_dl: float = 0
        self.tokenized: list[list[str]] = []
    
    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r'\w+', text.lower())
    
    def index(self, documents: list[dict]) -> None:
        """Проиндексировать документы. Каждый doc = {"text": ..., "source": ...}"""
        self.docs = documents
        self.tokenized = [self._tokenize(d["text"]) for d in documents]
        self.doc_lens = [len(t) for t in self.tokenized]
        self.avg_dl = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 1
        
        self.doc_freqs = defaultdict(int)
        for tokens in self.tokenized:
            for token in set(tokens):
                self.doc_freqs[token] += 1
    
    def search(self, query: str, top_k: int = 20) -> list[tuple[int, float]]:
        """Вернуть [(doc_index, score), ...] отсортированные по score DESC."""
        query_tokens = self._tokenize(query)
        n = len(self.docs)
        scores = []
        
        for i, doc_tokens in enumerate(self.tokenized):
            score = 0
            tf_map = Counter(doc_tokens)
            dl = self.doc_lens[i]
            
            for qt in query_tokens:
                if qt not in self.doc_freqs:
                    continue
                tf = tf_map.get(qt, 0)
                df = self.doc_freqs[qt]
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl))
                score += idf * tf_norm
            
            if score > 0:
                scores.append((i, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
