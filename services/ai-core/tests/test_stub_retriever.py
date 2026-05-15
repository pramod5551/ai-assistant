import pytest

from ai_assistant.search.stub_retriever import StubRetriever


@pytest.mark.asyncio
async def test_stub_retrieval_returns_policy_citation_for_library() -> None:
    r = StubRetriever()
    result = await r.search(("POLICIES",), "IETF requirement keywords")
    assert result.citations
    assert any(c.document_id == "ietf-bcp14-rfc2119" for c in result.citations)
    assert "MUST" in result.context_text or "SHOULD" in result.context_text


@pytest.mark.asyncio
async def test_stub_retrieval_empty_when_no_library_overlap() -> None:
    r = StubRetriever()
    result = await r.search(("OTHER_LIB",), "anything")
    assert not result.citations
    assert result.context_text == ""
