"""Tests for citation verification and tracking."""

import tempfile
from pathlib import Path

import pytest

from compass.services.citations import (
    Citation,
    VerifiedCitation,
    Answer,
    CitationExtractor,
    CitationVerifier,
    CitationFormatter,
)


class TestCitation:
    """Test Citation dataclass."""

    def test_create_citation(self):
        """Test creating a citation."""
        citation = Citation(
            doc_id="doc1",
            title="Python Guide",
            path="docs/python.html",
            page=5,
            section="Basics",
        )

        assert citation.doc_id == "doc1"
        assert citation.title == "Python Guide"
        assert citation.page == 5

    def test_citation_to_dict(self):
        """Test converting citation to dict."""
        citation = Citation(
            doc_id="doc1",
            title="Guide",
            path="docs/guide.html",
        )

        data = citation.to_dict()

        assert data["doc_id"] == "doc1"
        assert data["title"] == "Guide"
        assert "path" in data

    def test_citation_to_markdown(self):
        """Test markdown formatting."""
        citation = Citation(
            doc_id="doc1",
            title="Python Guide",
            path="docs/python.html",
            page=5,
        )

        markdown = citation.to_markdown()

        assert "Python Guide" in markdown
        assert "page 5" in markdown
        assert "docs/python.html" in markdown

    def test_citation_to_html(self):
        """Test HTML formatting."""
        citation = Citation(
            doc_id="doc1",
            title="Python Guide",
            path="docs/python.html",
        )

        html = citation.to_html()

        assert "Python Guide" in html
        assert "href=" in html
        assert "docs/python.html" in html


class TestAnswer:
    """Test Answer dataclass."""

    def test_create_answer(self):
        """Test creating an answer."""
        answer = Answer(content="Python is a language")

        assert answer.content == "Python is a language"
        assert answer.has_citations is False

    def test_add_citation_to_answer(self):
        """Test adding citation to answer."""
        answer = Answer(content="Python is a language")
        citation = Citation(
            doc_id="doc1",
            title="Guide",
            path="docs/guide.html",
        )

        answer.add_citation(citation)

        assert answer.has_citations is True
        assert len(answer.citations) == 1

    def test_answer_to_dict(self):
        """Test converting answer to dict."""
        answer = Answer(content="Test answer")
        answer.add_citation(
            Citation(doc_id="doc1", title="Guide", path="docs/guide.html")
        )

        data = answer.to_dict()

        assert data["content"] == "Test answer"
        assert len(data["citations"]) == 1
        assert data["has_citations"] is True


class TestCitationExtractor:
    """Test CitationExtractor class."""

    def test_extract_from_search_result(self):
        """Test extracting citation from search result."""
        result = {
            "doc_id": "doc1",
            "title": "Python Guide",
            "path": "docs/python.html",
            "preview": "Python is a language",
            "score": 0.95,
        }

        citation = CitationExtractor.extract_from_search_result(result)

        assert citation is not None
        assert citation.title == "Python Guide"
        assert citation.confidence == 0.95

    def test_extract_from_html_result(self):
        """Test extracting citation from HTML result."""
        result = {
            "title": "HTML Guide",
            "url": "docs/html.html",
            "content": "HTML is markup",
        }

        citation = CitationExtractor.extract_from_html_result(result, doc_id="doc1")

        assert citation is not None
        assert citation.title == "HTML Guide"
        assert citation.doc_id == "doc1"

    def test_extract_from_pdf_result(self):
        """Test extracting citation from PDF result."""
        result = {
            "title": "PDF Guide",
            "url": "docs/guide.pdf",
            "content": "PDF content",
        }

        citation = CitationExtractor.extract_from_pdf_result(result, page=5)

        assert citation is not None
        assert citation.page == 5

    def test_extract_from_tool_output_search(self):
        """Test extracting citations from search tool output."""
        output = {
            "results": [
                {
                    "doc_id": "doc1",
                    "title": "Guide 1",
                    "path": "docs/1.html",
                    "score": 0.9,
                },
                {
                    "doc_id": "doc2",
                    "title": "Guide 2",
                    "path": "docs/2.html",
                    "score": 0.8,
                },
            ]
        }

        citations = CitationExtractor.extract_from_tool_output("lexical_search", output)

        assert len(citations) == 2
        assert citations[0].title == "Guide 1"

    def test_extract_from_tool_output_html(self):
        """Test extracting citations from HTML tool output."""
        output = {
            "title": "HTML Doc",
            "url": "docs/html.html",
            "content": "Content",
        }

        citations = CitationExtractor.extract_from_tool_output("read_html", output)

        assert len(citations) == 1
        assert citations[0].title == "HTML Doc"


class TestCitationVerifier:
    """Test CitationVerifier class."""

    def test_verify_document_exists_true(self):
        """Test verifying document exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.html"
            doc_file.write_text("<html>Test</html>")

            citation = Citation(
                doc_id="doc1",
                title="Test",
                path=str(doc_file),
            )

            result = CitationVerifier.verify_document_exists(citation)

            assert result is True

    def test_verify_document_exists_false(self):
        """Test verifying non-existent document."""
        citation = Citation(
            doc_id="doc1",
            title="Test",
            path="/nonexistent/path.html",
        )

        result = CitationVerifier.verify_document_exists(citation)

        assert result is False

    def test_verify_content_match_true(self):
        """Test content match verification succeeds."""
        citation = Citation(
            doc_id="doc1",
            title="Guide",
            path="docs/guide.html",
            snippet="Python programming language",
        )

        answer = "Python is a powerful programming language for development"

        result = CitationVerifier.verify_content_match(citation, answer)

        assert result is True

    def test_verify_content_match_false(self):
        """Test content match verification fails."""
        citation = Citation(
            doc_id="doc1",
            title="Guide",
            path="docs/guide.html",
            snippet="Java Enterprise Edition",
        )

        answer = "Python is a programming language"

        result = CitationVerifier.verify_content_match(citation, answer)

        assert result is False

    def test_verify_citation_with_existence_check(self):
        """Test full citation verification with existence check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_file = Path(tmpdir) / "doc.html"
            doc_file.write_text("Content")

            citation = Citation(
                doc_id="doc1",
                title="Guide",
                path=str(doc_file),
                snippet="Content",
            )

            verified = CitationVerifier.verify_citation(
                citation,
                "The Content is important",
                verify_existence=True,
                verify_content=True,
            )

            assert verified.verified is True
            assert verified.citation.doc_id == "doc1"


class TestCitationFormatter:
    """Test CitationFormatter class."""

    def test_format_citations_markdown(self):
        """Test markdown formatting of citations."""
        citations = [
            Citation(doc_id="doc1", title="Guide 1", path="docs/1.html"),
            Citation(doc_id="doc2", title="Guide 2", path="docs/2.html"),
        ]

        markdown = CitationFormatter.format_citations_markdown(citations)

        assert "Citations" in markdown
        assert "Guide 1" in markdown
        assert "Guide 2" in markdown
        assert "[" in markdown and "]" in markdown

    def test_format_citations_markdown_empty(self):
        """Test markdown formatting with empty citations."""
        markdown = CitationFormatter.format_citations_markdown([])

        assert markdown == ""

    def test_format_citations_html(self):
        """Test HTML formatting of citations."""
        citations = [
            Citation(doc_id="doc1", title="Guide", path="docs/guide.html"),
        ]

        html = CitationFormatter.format_citations_html(citations)

        assert "<ol>" in html
        assert "<li>" in html
        assert "Guide" in html
        assert "href=" in html

    def test_format_answer_with_citations_markdown(self):
        """Test formatting answer with citations."""
        answer = Answer(content="Python is great")
        answer.add_citation(
            Citation(doc_id="doc1", title="Guide", path="docs/guide.html")
        )

        formatted = CitationFormatter.format_answer_with_citations(
            answer, format_type="markdown"
        )

        assert "Python is great" in formatted
        assert "Citations" in formatted
        assert "Guide" in formatted

    def test_format_answer_without_citations(self):
        """Test formatting answer without citations."""
        answer = Answer(content="Python is great")

        formatted = CitationFormatter.format_answer_with_citations(answer)

        assert "Python is great" in formatted
        # Should not have citations section
        assert "Citations" not in formatted

    def test_generate_citation_index(self):
        """Test generating citation index."""
        citations = [
            Citation(
                doc_id="doc1",
                title="Guide 1",
                path="docs/guide1.html",
                section="Intro",
            ),
            Citation(
                doc_id="doc2",
                title="Guide 2",
                path="docs/guide1.html",
                section="Advanced",
            ),
        ]

        index = CitationFormatter.generate_citation_index(citations)

        assert "docs/guide1.html" in index
        assert len(index["docs/guide1.html"]["citations"]) == 2
        assert index["docs/guide1.html"]["title"] == "Guide 1"
