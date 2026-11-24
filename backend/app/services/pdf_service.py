"""Extracts raw text (and per-page text) from uploaded PDFs.

We deliberately avoid any computer-vision / OCR-on-image approach for the
soil report path (see Engineering Principle: "No Computer Vision in the
core system") -- reports are assumed to be text-based PDFs (scanned Soil
Health Cards would need an OCR pre-step, which is out of scope for now).
"""
from __future__ import annotations

import fitz  # PyMuPDF


def extract_text(pdf_path: str) -> str:
    """Extract plain text from every page of a PDF, concatenated."""
    doc = fitz.open(pdf_path)
    try:
        pages = [page.get_text("text") for page in doc]
    finally:
        doc.close()
    return "\n".join(pages)


def extract_pages(pdf_path: str) -> list[str]:
    """Return a list of per-page text blocks (used for RAG chunking so we
    can keep page-level provenance for the 'Why this recommendation?'
    source citations).
    """
    doc = fitz.open(pdf_path)
    try:
        return [page.get_text("text") for page in doc]
    finally:
        doc.close()
