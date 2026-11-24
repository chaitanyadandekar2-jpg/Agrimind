"""LangChain BaseRetriever adapter for AgriMind's ChromaDB Knowledge Store.

Integrates ChromaDB with LangChain's retrieval interface, supporting
semantic search, metadata filtering, keyword reranking, and source attribution.
"""
from __future__ import annotations

import re
from typing import List, Optional, Dict, Any
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import Field

from app.rag import vector_store
from app.rag.embedding_service import embed_query
from app.models.recommendation import Evidence


class AgriMindChromaRetriever(BaseRetriever):
    """LangChain Retriever backed by the existing ChromaDB collection."""

    top_k: int = Field(default=4, description="Number of documents to retrieve")
    category: Optional[str] = Field(default=None, description="Optional metadata category filter")
    score_threshold: float = Field(default=0.0, description="Minimum similarity score")

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        try:
            if vector_store.count() == 0:
                return []

            embedding = embed_query(query)
            where = {"category": self.category} if self.category else None
            # Retrieve extra candidates for reranking
            candidate_k = min(vector_store.count(), max(self.top_k * 2, 8))
            results = vector_store.query(embedding, top_k=candidate_k, where=where)

            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]

            scored_docs: List[tuple[float, Document]] = []
            query_words = set(re.findall(r"\b\w{3,}\b", query.lower()))

            for text, meta, dist in zip(docs, metas, dists):
                similarity = max(0.0, 1.0 - dist)
                if similarity < self.score_threshold:
                    continue

                # Hybrid keyword match bonus (up to +0.08)
                text_lower = text.lower()
                overlap_count = sum(1 for w in query_words if w in text_lower)
                bonus = min(0.08, overlap_count * 0.02)
                final_score = round(min(1.0, similarity + bonus), 3)

                meta_copy = dict(meta) if meta else {}
                meta_copy["score"] = final_score

                doc = Document(page_content=text, metadata=meta_copy)
                scored_docs.append((final_score, doc))

            # Sort by final score descending
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            return [doc for _, doc in scored_docs[: self.top_k]]
        except Exception:
            return []


def get_langchain_retriever(top_k: int = 4, category: Optional[str] = None) -> AgriMindChromaRetriever:
    """Factory function to get a configured LangChain retriever."""
    return AgriMindChromaRetriever(top_k=top_k, category=category)


def retrieve_evidence(query_text: str, top_k: int = 4, category: Optional[str] = None) -> List[Evidence]:
    """Retrieve evidence documents formatted as Evidence models."""
    try:
        retriever = get_langchain_retriever(top_k=top_k, category=category)
        docs = retriever.invoke(query_text)

        evidence_list: List[Evidence] = []
        for doc in docs:
            score = doc.metadata.get("score", 0.75)
            source = doc.metadata.get("source", "knowledge_base")
            evidence_list.append(Evidence(text=doc.page_content, source=source, score=score))
        return evidence_list
    except Exception:
        return []
