from __future__ import annotations

from app.models.recommendation import Evidence
from app.rag.langchain_retriever import retrieve_evidence, get_langchain_retriever


def retrieve(query_text: str, top_k: int = 4, category: str | None = None) -> list[Evidence]:
    """Semantic search over the indexed knowledge base via LangChain ChromaDB retriever.

    Returns Evidence objects (text/source/score) directly usable in the
    'Why this recommendation?' panel, agent tasks, and LLM context.
    """
    return retrieve_evidence(query_text, top_k=top_k, category=category)
