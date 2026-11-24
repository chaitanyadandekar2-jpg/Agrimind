"""Run this to (re)build the ChromaDB index from data/knowledge/**.

Usage:
    python -m app.rag.index_knowledge
"""
from __future__ import annotations

import hashlib

from app.rag.knowledge_loader import load_documents
from app.rag.chunker import chunk_documents
from app.rag.embedding_service import embed_texts
from app.rag import vector_store


def build_index(reset: bool = True) -> int:
    if reset:
        vector_store.reset_collection()

    docs = load_documents()
    if not docs:
        print("No documents found under data/knowledge/. Nothing to index.")
        return 0

    chunks = chunk_documents(docs)
    print(f"Loaded {len(docs)} documents -> {len(chunks)} chunks.")

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)

    ids = [hashlib.sha1(f"{c.source}:{i}:{c.text[:50]}".encode()).hexdigest() for i, c in enumerate(chunks)]
    metadatas = [{"source": c.source, "category": c.category, "heading": c.heading or ""} for c in chunks]

    vector_store.upsert_chunks(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    print(f"Indexed {len(chunks)} chunks into ChromaDB collection '{vector_store.COLLECTION_NAME}'.")
    return len(chunks)


if __name__ == "__main__":
    build_index()
