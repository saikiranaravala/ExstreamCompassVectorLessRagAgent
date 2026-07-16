"""Tests for the retrieval layer (corpus, BM25, passages, service)."""

import pytest

from compass.retrieval.bm25 import BM25Index
from compass.retrieval.corpus import CorpusStore, DocRecord
from compass.retrieval.passages import best_passage
from compass.retrieval.service import QueryService
from compass.retrieval.textutil import extract_html_text, tokenize


# ------------------------------------------------------------------ fixtures --


def _doc(doc_id: str, title: str, text: str, variant: str = "CloudNative") -> DocRecord:
    return DocRecord(doc_id=doc_id, variant=variant, path=doc_id, title=title, text=text)


@pytest.fixture
def mini_corpus(tmp_path):
    """A tiny docs tree with two variants."""
    for variant, topics in {
        "CloudNative": {
            "deploy.htm": ("Deploying with Kubernetes", "Deploy the Exstream engine to a Kubernetes cluster using Helm charts. Configure the orchestration service before deployment."),
            "empower.htm": ("Empower editor", "Empower lets business users edit documents in a browser."),
        },
        "ServerBased": {
            "install.htm": ("Installing the server", "Install the Exstream server on Windows. Run the installer and configure the database connection."),
        },
    }.items():
        folder = tmp_path / "docs" / variant / "HTML" / "Content"
        folder.mkdir(parents=True)
        for name, (title, body) in topics.items():
            words = (body + " ") * 3  # pass the MIN_WORDS filter
            (folder / name).write_text(
                f"<html><head><title>{title}</title><style>p{{}}</style></head>"
                f"<body><p>{words}</p><script>var x=1;</script></body></html>",
                encoding="utf-8",
            )
    return tmp_path / "docs"


# ------------------------------------------------------------------ textutil --


class TestTextUtil:
    def test_tokenize_folds_plurals_and_stopwords(self):
        tokens = tokenize("The engines are running processes")
        assert "engine" in tokens
        assert "the" not in tokens and "are" not in tokens

    def test_extract_html_text_strips_chrome(self):
        title, text = extract_html_text(
            "<html><head><title>My Topic</title><style>.x{color:red}</style></head>"
            "<body><script>alert(1)</script><p>Real   content here</p></body></html>"
        )
        assert title == "My Topic"
        assert "Real content here" in text
        assert "alert" not in text and "color" not in text


# ---------------------------------------------------------------------- bm25 --


class TestBM25:
    def test_ranks_relevant_doc_first(self):
        docs = [
            _doc("a.htm", "Printing output", "printer output queues and drivers " * 5),
            _doc("b.htm", "Kubernetes deployment", "deploy pods to the kubernetes cluster " * 5),
            _doc("c.htm", "Fonts", "font management and typefaces " * 5),
        ]
        index = BM25Index(docs)
        hits = index.search("deploy to kubernetes")
        assert hits and hits[0].doc.doc_id == "b.htm"

    def test_title_match_outranks_passing_mention(self):
        docs = [
            _doc("mention.htm", "Other topic", "empower is mentioned once. " + "filler words here " * 50),
            _doc("topic.htm", "Using Empower", "empower empower editing documents. " + "filler words here " * 50),
        ]
        index = BM25Index(docs)
        hits = index.search("empower")
        assert hits[0].doc.doc_id == "topic.htm"

    def test_empty_query_and_no_match(self):
        index = BM25Index([_doc("a.htm", "T", "some text")])
        assert index.search("") == []
        assert index.search("zzzunknownterm") == []


# ------------------------------------------------------------------ passages --


class TestPassages:
    def test_returns_window_containing_terms(self):
        filler = "irrelevant words about nothing in particular " * 40
        nugget = "To configure the output queue open the orchestration console and select queue settings."
        text = filler + nugget + " " + filler
        index = BM25Index([_doc("x.htm", "X", text)])
        terms = index.query_terms("configure output queue")
        passage = best_passage(text, terms)
        assert "output queue" in passage
        assert len(passage) <= 950

    def test_short_doc_returned_whole(self):
        assert best_passage("short text", {"short": 1.0}) == "short text"


# ------------------------------------------------------------------- service --


class TestQueryService:
    def test_end_to_end_without_llm(self, mini_corpus, tmp_path, monkeypatch):
        # Ensure the extractive fallback path (no API key)
        from compass.config import settings

        monkeypatch.setattr(settings, "openrouter_api_key", "")

        service = QueryService(docs_root=mini_corpus, cache_dir=tmp_path / ".atlas")
        result = service.query("deploy kubernetes helm", "CloudNative")

        assert result["citations"], "expected at least one citation"
        assert result["citations"][0]["path"].endswith("deploy.htm")
        assert "Kubernetes" in result["answer"]
        assert result["tool_calls"] >= 2
        assert result["trace"]

    def test_variant_isolation(self, mini_corpus, tmp_path, monkeypatch):
        from compass.config import settings

        monkeypatch.setattr(settings, "openrouter_api_key", "")

        service = QueryService(docs_root=mini_corpus, cache_dir=tmp_path / ".atlas")
        hits = service.search("install server database", "CloudNative")
        assert all("ServerBased" not in h["path"] for h in hits)

    def test_corpus_cache_roundtrip(self, mini_corpus, tmp_path):
        store = CorpusStore(mini_corpus, tmp_path / ".atlas")
        built = store.load("CloudNative")
        cached = store.load("CloudNative")
        assert [d.doc_id for d in built] == [d.doc_id for d in cached]
        assert store.cache_path("CloudNative").exists()

    def test_get_document_refuses_cross_variant(self, mini_corpus, tmp_path):
        store = CorpusStore(mini_corpus, tmp_path / ".atlas")
        ok = store.get_document("CloudNative", "CloudNative/HTML/Content/deploy.htm")
        assert ok is not None and ok.title == "Deploying with Kubernetes"
        # Same file requested under the wrong variant must be refused
        blocked = store.get_document("ServerBased", "CloudNative/HTML/Content/deploy.htm")
        assert blocked is None
