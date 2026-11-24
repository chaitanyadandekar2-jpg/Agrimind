from app.rag.knowledge_loader import RawDocument
from app.rag.chunker import chunk_document


def test_heading_kept_as_context():
    doc = RawDocument(
        text="# Nitrogen\nNitrogen is important.\n\n# Phosphorus\nPhosphorus is also important.",
        source="test.md",
        category="soil",
    )
    chunks = chunk_document(doc)
    headings = {c.heading for c in chunks}
    assert "Nitrogen" in headings
    assert "Phosphorus" in headings


def test_qa_pair_not_split_apart():
    doc = RawDocument(
        text="# FAQ\nQ: What is the ideal pH for tomato?\n\nA: Between 6.0 and 6.8.\n\nQ: What about wheat?\n\nA: 6.0 to 7.5.",
        source="faq.md",
        category="crops",
    )
    chunks = chunk_document(doc)
    combined_texts = [c.text for c in chunks]
    # Each question should appear in the SAME chunk as its answer.
    tomato_chunk = next(t for t in combined_texts if "tomato" in t.lower())
    assert "6.0 and 6.8" in tomato_chunk


def test_sliding_window_applies_overlap_and_terminates():
    """Regression test: the overlap used to be dead code
    (start = max(end - overlap, end) always equalled end), so long
    sections were split with NO shared context between chunks.
    """
    from app.rag.chunker import _sliding_window

    words = [f"w{i}" for i in range(400)]
    text = " ".join(words)  # ~1,900 chars, well over max_chars
    chunks = _sliding_window(text, max_chars=300, overlap=60)

    assert len(chunks) > 1
    # Neighbouring chunks must share some text (the overlap).
    for a, b in zip(chunks, chunks[1:]):
        shared = set(a.split()) & set(b.split())
        assert len(shared) >= 5, "neighbouring chunks should share ~overlap chars of context"
    # Nothing is lost: every word appears in at least one chunk.
    seen = set(" ".join(chunks).split())
    assert set(words) <= seen
    # No duplicate tail chunk at the end.
    assert chunks[-1] != chunks[-2]


def test_sliding_window_short_text_is_single_chunk():
    from app.rag.chunker import _sliding_window

    assert _sliding_window("short text", max_chars=300, overlap=60) == ["short text"]
