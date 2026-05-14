import os
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_documents(knowledge_dir: str) -> list[str]:
    """Загрузить все .txt файлы из папки и вернуть список текстов."""
    documents = []
    if not os.path.exists(knowledge_dir):
        return []
    for filename in os.listdir(knowledge_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(knowledge_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                documents.append(f.read())
    return documents


def split_into_chunks(documents: list[str], chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """Разбить документы на чанки для эмбеддингов."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for doc in documents:
        chunks.extend(splitter.split_text(doc))
    return chunks
