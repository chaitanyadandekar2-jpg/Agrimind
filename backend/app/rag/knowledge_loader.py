"""Walks data/knowledge/** and loads raw documents for chunking/indexing.

Supports .md / .txt as free text, and treats each top-level category folder
name (soil, crops, fertilizer, organic, pesticides) as metadata so retrieval
results can be filtered/labelled by category later if needed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge")


@dataclass
class RawDocument:
    text: str
    source: str        # relative file path, used for citations
    category: str       # soil | crops | fertilizer | organic | pesticides


def load_documents(knowledge_dir: str = KNOWLEDGE_DIR) -> list[RawDocument]:
    docs: list[RawDocument] = []
    knowledge_dir = os.path.abspath(knowledge_dir)

    for category in sorted(os.listdir(knowledge_dir)):
        category_path = os.path.join(knowledge_dir, category)
        if not os.path.isdir(category_path):
            continue
        for fname in sorted(os.listdir(category_path)):
            if not fname.lower().endswith((".md", ".txt")):
                continue
            fpath = os.path.join(category_path, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()
            docs.append(
                RawDocument(
                    text=text,
                    source=f"{category}/{fname}",
                    category=category,
                )
            )
    return docs
