from ai_search_assistant.ingestion.text_chunker import chunk_plain_text


def test_chunk_plain_text_splits_long_prose():
    text = "alpha. " * 400
    chunks = chunk_plain_text(text, max_chars=200, overlap=20)
    assert len(chunks) >= 2
    assert all(len(c) <= 250 for c in chunks)


def test_chunk_plain_text_empty():
    assert chunk_plain_text("") == []
    assert chunk_plain_text("   ") == []


def test_chunk_plain_text_short_unchanged():
    s = "One short paragraph."
    assert chunk_plain_text(s, max_chars=1000) == [s]
