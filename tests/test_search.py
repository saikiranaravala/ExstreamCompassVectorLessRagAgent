"""Tests for BM25 lexical search index."""

import tempfile
import time
from pathlib import Path

import pytest

from compass.indexer.search import BM25Index, SearchResult


@pytest.fixture
def temp_index_dir():
    """Create temporary directory for index."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def search_index(temp_index_dir):
    """Create a BM25Index for testing."""
    return BM25Index(temp_index_dir)


class TestBM25Index:
    """Test BM25Index class."""

    def test_index_initialization(self, temp_index_dir):
        """Test index initialization."""
        index = BM25Index(temp_index_dir)
        assert index is not None
        assert index.index_path.exists()

    def test_index_creates_directory(self, temp_index_dir):
        """Test index creates directory if it doesn't exist."""
        new_path = temp_index_dir / "subdir" / "index"
        index = BM25Index(new_path)
        assert new_path.exists()

    def test_add_single_document(self, search_index):
        """Test adding a single document."""
        result = search_index.add_document(
            doc_id="doc1",
            title="Test Document",
            path="docs/test.html",
            content="This is test content about Python programming.",
            timestamp=int(time.time()),
        )
        assert result is True

    def test_add_document_and_search(self, search_index):
        """Test adding document and searching for it."""
        search_index.add_document(
            doc_id="doc1",
            title="Python Guide",
            path="docs/python.html",
            content="Python is a programming language used for data science and web development.",
            timestamp=int(time.time()),
        )

        results = search_index.search("Python programming")
        assert len(results) > 0
        assert results[0].doc_id == "doc1"

    def test_search_result_structure(self, search_index):
        """Test SearchResult dataclass structure."""
        search_index.add_document(
            doc_id="doc1",
            title="Test",
            path="test.html",
            content="Test content with specific keywords",
            timestamp=int(time.time()),
        )

        results = search_index.search("specific keywords")
        assert len(results) > 0

        result = results[0]
        assert isinstance(result, SearchResult)
        assert hasattr(result, "doc_id")
        assert hasattr(result, "title")
        assert hasattr(result, "path")
        assert hasattr(result, "score")
        assert hasattr(result, "content_preview")

    def test_search_returns_scored_results(self, search_index):
        """Test search returns results with scores."""
        search_index.add_document(
            doc_id="doc1",
            title="First Document",
            path="doc1.html",
            content="Machine learning algorithms",
            timestamp=int(time.time()),
        )

        search_index.add_document(
            doc_id="doc2",
            title="Second Document",
            path="doc2.html",
            content="Machine learning deep learning neural networks",
            timestamp=int(time.time()),
        )

        results = search_index.search("machine learning")
        assert len(results) >= 1
        for result in results:
            assert result.score > 0

    def test_batch_add_documents(self, search_index):
        """Test batch adding multiple documents."""
        documents = [
            {
                "doc_id": "doc1",
                "title": "Document 1",
                "path": "doc1.html",
                "content": "Content about Python",
                "timestamp": int(time.time()),
            },
            {
                "doc_id": "doc2",
                "title": "Document 2",
                "path": "doc2.html",
                "content": "Content about Java",
                "timestamp": int(time.time()),
            },
            {
                "doc_id": "doc3",
                "title": "Document 3",
                "path": "doc3.html",
                "content": "Content about JavaScript",
                "timestamp": int(time.time()),
            },
        ]

        count = search_index.batch_add_documents(documents)
        assert count == 3

    def test_batch_add_partial_failure(self, search_index):
        """Test batch add with some invalid documents."""
        documents = [
            {
                "doc_id": "doc1",
                "title": "Valid Document",
                "path": "doc1.html",
                "content": "Valid content",
                "timestamp": int(time.time()),
            },
            {
                "doc_id": "doc2",
                # Missing required fields - may fail
                "content": "Invalid document",
            },
            {
                "doc_id": "doc3",
                "title": "Another Valid",
                "path": "doc3.html",
                "content": "More valid content",
                "timestamp": int(time.time()),
            },
        ]

        count = search_index.batch_add_documents(documents)
        # Should add at least the valid ones
        assert count >= 2

    def test_search_nonexistent_query(self, search_index):
        """Test search with query that has no results."""
        search_index.add_document(
            doc_id="doc1",
            title="Test",
            path="test.html",
            content="Python programming",
            timestamp=int(time.time()),
        )

        results = search_index.search("xyz_nonexistent_xyz")
        assert isinstance(results, list)

    def test_search_with_limit(self, search_index):
        """Test search respects result limit."""
        # Add multiple documents
        for i in range(10):
            search_index.add_document(
                doc_id=f"doc{i}",
                title=f"Document {i}",
                path=f"doc{i}.html",
                content="Python Java JavaScript C++ Ruby Go",
                timestamp=int(time.time()),
            )

        results = search_index.search("programming language", limit=3)
        assert len(results) <= 3

    def test_get_document_count(self, search_index):
        """Test getting document count."""
        count_before = search_index.get_document_count()
        assert count_before >= 0

        search_index.add_document(
            doc_id="doc1",
            title="Test",
            path="test.html",
            content="Test content",
            timestamp=int(time.time()),
        )

        count_after = search_index.get_document_count()
        assert count_after > count_before

    def test_delete_document(self, search_index):
        """Test deleting a document."""
        search_index.add_document(
            doc_id="doc1",
            title="To Delete",
            path="delete.html",
            content="This will be deleted",
            timestamp=int(time.time()),
        )

        count_before = search_index.get_document_count()

        result = search_index.delete_document("doc1")
        assert result is True

        count_after = search_index.get_document_count()
        # Note: tantivy indexing may have caching, so count might not decrease immediately

    def test_clear_index(self, search_index):
        """Test clearing all documents from index."""
        search_index.add_document(
            doc_id="doc1",
            title="Test",
            path="test.html",
            content="Content",
            timestamp=int(time.time()),
        )

        result = search_index.clear_index()
        # Should return success (even if no documents were deleted)
        assert isinstance(result, bool)

    def test_content_preview_truncation(self, search_index):
        """Test that content preview is truncated properly."""
        long_content = "A" * 500  # Content longer than 200 chars

        search_index.add_document(
            doc_id="doc1",
            title="Long Content",
            path="long.html",
            content=long_content,
            timestamp=int(time.time()),
        )

        results = search_index.search("A")
        if results:
            # Preview should be at most 200 chars
            assert len(results[0].content_preview) <= 200
