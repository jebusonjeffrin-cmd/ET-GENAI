from app.stores.keyword_store import FakeKeywordStore
from app.stores.vector_store import VectorRecord


def _record(id_: str, text: str) -> VectorRecord:
    return VectorRecord(id=id_, document_id=id_, text=text, vector=[])


def test_keyword_search_finds_overlapping_tokens():
    store = FakeKeywordStore()
    store.index(_record("a", "Pump P-101 bearing replacement work order"))
    store.index(_record("b", "Valve V-200 seal inspection procedure"))

    results = store.search("bearing replacement pump")

    assert len(results) == 1
    assert results[0][0].id == "a"
    assert results[0][1] > 0


def test_keyword_search_ranks_higher_overlap_first():
    store = FakeKeywordStore()
    store.index(_record("low", "pump maintenance notes"))
    store.index(_record("high", "pump bearing vibration alarm maintenance"))

    results = store.search("pump bearing vibration maintenance")

    assert [r[0].id for r in results] == ["high", "low"]


def test_keyword_search_returns_empty_for_no_match():
    store = FakeKeywordStore()
    store.index(_record("a", "completely unrelated content"))
    assert store.search("nonexistent query terms") == []


def test_keyword_search_respects_top_k():
    store = FakeKeywordStore()
    for i in range(10):
        store.index(_record(str(i), "pump maintenance record"))
    results = store.search("pump maintenance", top_k=3)
    assert len(results) == 3
