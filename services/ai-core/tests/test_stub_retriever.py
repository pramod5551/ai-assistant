import pytest

from ai_search_assistant.search.stub_retriever import StubRetriever


@pytest.mark.asyncio
async def test_stub_retrieval_returns_empty_without_seeded_corpus() -> None:
    r = StubRetriever()
    result = await r.search(("POLICIES",), "anything")
    assert not result.citations
    assert result.context_text == ""


@pytest.mark.asyncio
async def test_stub_retrieval_empty_when_no_library_overlap() -> None:
    r = StubRetriever()
    result = await r.search(("OTHER_LIB",), "anything")
    assert not result.citations
    assert result.context_text == ""
