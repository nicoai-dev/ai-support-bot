import os
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_documents(knowledge_dir: str) -> list[dict]:
    """Загрузить все .txt файлы и вернуть список словарей {'text', 'source'}."""
    documents = []
    if not os.path.exists(knowledge_dir):
        return []
    for filename in os.listdir(knowledge_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(knowledge_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                documents.append({
                    "text": f.read(),
                    "source": filename
                })
    return documents


def split_into_chunks(documents: list[dict], chunk_size: int = 500, chunk_overlap: int = 50) -> list[dict]:
    """Разбить документы на чанки, сохраняя метаданные."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    all_chunks = []
    for doc in documents:
        text_chunks = splitter.split_text(doc["text"])
        for chunk in text_chunks:
            all_chunks.append({
                "text": chunk,
                "source": doc["source"]
            })
    return all_chunks
