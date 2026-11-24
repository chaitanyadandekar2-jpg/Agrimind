"""Chunking strategy for the RAG pipeline.

This is the piece the project explicitly calls out as needing quality work
(Phase 4): a naive fixed-length splitter cuts an FAQ's question away from
its answer, or a heading away from the paragraph that explains it. Instead
we:

1. Split on markdown headings first (##, #) so each section stays whole.
2. Within a section, if it looks like a Q/A pair (starts with "Q:"/"Question"
   or ends with "?" on its own line followed by an answer), keep the pair
   together rather than splitting on paragraph boundaries.
3. Only fall back to a sliding window over raw text when a section is
   larger than `max_chars`, and even then we split on paragraph
   boundaries (blank lines) rather than mid-sentence.

Each chunk keeps its originating heading as context prefix, which both
improves embedding quality and gives us a natural citation label.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.rag.knowledge_loader import RawDocument

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
QA_START_RE = re.compile(r"^\s*(Q(?:uestion)?\s*[:.\)]|Q\d+[:.\)])", re.IGNORECASE)


@dataclass
class Chunk:
    text: str
    source: str
    category: str
    heading: str | None


def _split_by_headings(text: str) -> list[tuple[str | None, str]]:
    """Return list of (heading, section_text) preserving heading context."""
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [(None, text)]

    sections: list[tuple[str | None, str]] = []
    for i, m in enumerate(matches):
        heading = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((heading, body))
    return sections


def _keep_qa_pairs_together(section_text: str) -> list[str]:
    """Split a section into paragraph-like units, but re-merge a
    question-looking line with the paragraph that follows it (its answer)
    so retrieval never returns a dangling question with no answer.
    """
    raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section_text) if p.strip()]
    units: list[str] = []
    i = 0
    while i < len(raw_paragraphs):
        para = raw_paragraphs[i]
        looks_like_question = bool(QA_START_RE.match(para)) or para.rstrip().endswith("?")
        is_short_question_only = looks_like_question and len(para) < 200
        if is_short_question_only and i + 1 < len(raw_paragraphs):
            units.append(para + "\n" + raw_paragraphs[i + 1])
            i += 2
        else:
            units.append(para)
            i += 1
    return units


def _sliding_window(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # try not to cut mid-word
        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break  # reached the end; without this the overlap would emit a duplicate tail chunk
        # Step back by `overlap` chars so neighbouring chunks share context,
        # but never move backwards or stand still (guards against an
        # infinite loop when the last-space cut made this chunk very short).
        next_start = end - overlap
        start = next_start if next_start > start else end
    return [c for c in chunks if c]


def chunk_document(doc: RawDocument, max_chars: int = 900, overlap: int = 100) -> list[Chunk]:
    chunks: list[Chunk] = []
    for heading, section_text in _split_by_headings(doc.text):
        units = _keep_qa_pairs_together(section_text)
        for unit in units:
            for piece in _sliding_window(unit, max_chars=max_chars, overlap=overlap):
                prefixed = f"{heading}\n{piece}" if heading else piece
                chunks.append(
                    Chunk(text=prefixed, source=doc.source, category=doc.category, heading=heading)
                )
    return chunks


def chunk_documents(docs: list[RawDocument], **kwargs) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc, **kwargs))
    return all_chunks
