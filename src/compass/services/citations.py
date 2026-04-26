"""Citation verification and tracking."""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A citation to a source document."""

    doc_id: str
    title: str
    path: str
    page: Optional[int] = None
    section: Optional[str] = None
    snippet: Optional[str] = None
    confidence: float = 1.0  # 0.0 to 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "path": self.path,
            "page": self.page,
            "section": self.section,
            "snippet": self.snippet,
            "confidence": self.confidence,
        }

    def to_markdown(self) -> str:
        """Format citation as markdown."""
        base = f"[{self.title}]({self.path})"

        if self.page:
            base += f" (page {self.page})"

        if self.section:
            base += f" - {self.section}"

        return base

    def to_html(self) -> str:
        """Format citation as HTML."""
        base = f'<a href="{self.path}">{self.title}</a>'

        if self.page:
            base += f" (page {self.page})"

        if self.section:
            base += f" - {self.section}"

        return base


@dataclass
class VerifiedCitation:
    """Citation with verification status."""

    citation: Citation
    verified: bool
    verification_method: str  # "content_match", "document_exists", "manual_review"
    verification_timestamp: Optional[str] = None
    verification_notes: Optional[str] = None


@dataclass
class Answer:
    """Generated answer with citations."""

    content: str
    citations: list[Citation] = field(default_factory=list)
    has_citations: bool = field(default=False)
    all_citations_verified: bool = field(default=False)

    def add_citation(self, citation: Citation) -> None:
        """Add citation to answer."""
        self.citations.append(citation)
        self.has_citations = True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "citations": [c.to_dict() for c in self.citations],
            "has_citations": self.has_citations,
            "all_citations_verified": self.all_citations_verified,
        }


class CitationExtractor:
    """Extract citations from tool results."""

    @staticmethod
    def extract_from_search_result(result: dict) -> Optional[Citation]:
        """Extract citation from search result.

        Args:
            result: Search result dict

        Returns:
            Citation or None
        """
        try:
            return Citation(
                doc_id=result.get("doc_id", "unknown"),
                title=result.get("title", "Untitled"),
                path=result.get("path", ""),
                snippet=result.get("preview", ""),
                confidence=min(1.0, result.get("score", 0.5)),
            )
        except Exception as e:
            logger.warning(f"Failed to extract citation from search result: {e}")
            return None

    @staticmethod
    def extract_from_html_result(result: dict, doc_id: Optional[str] = None) -> Optional[Citation]:
        """Extract citation from HTML read result.

        Args:
            result: HTML read result dict
            doc_id: Optional document ID

        Returns:
            Citation or None
        """
        try:
            return Citation(
                doc_id=doc_id or result.get("url", "unknown"),
                title=result.get("title", "Untitled"),
                path=result.get("url", ""),
                snippet=result.get("content", "")[:200],
                confidence=0.95,  # Direct read is high confidence
            )
        except Exception as e:
            logger.warning(f"Failed to extract citation from HTML result: {e}")
            return None

    @staticmethod
    def extract_from_pdf_result(
        result: dict,
        doc_id: Optional[str] = None,
        page: Optional[int] = None,
    ) -> Optional[Citation]:
        """Extract citation from PDF read result.

        Args:
            result: PDF read result dict
            doc_id: Optional document ID
            page: Optional page number

        Returns:
            Citation or None
        """
        try:
            return Citation(
                doc_id=doc_id or result.get("url", "unknown"),
                title=result.get("title", "Untitled"),
                path=result.get("url", ""),
                page=page,
                snippet=result.get("content", "")[:200],
                confidence=0.95,  # Direct read is high confidence
            )
        except Exception as e:
            logger.warning(f"Failed to extract citation from PDF result: {e}")
            return None

    @staticmethod
    def extract_from_tool_output(tool_name: str, output: dict) -> list[Citation]:
        """Extract all citations from tool output.

        Args:
            tool_name: Name of tool that produced output
            output: Tool output dict

        Returns:
            List of extracted citations
        """
        citations = []

        if tool_name == "lexical_search" and "results" in output:
            for result in output["results"]:
                citation = CitationExtractor.extract_from_search_result(result)
                if citation:
                    citations.append(citation)

        elif tool_name == "read_html" and output:
            citation = CitationExtractor.extract_from_html_result(output)
            if citation:
                citations.append(citation)

        elif tool_name == "read_pdf" and output:
            citation = CitationExtractor.extract_from_pdf_result(output)
            if citation:
                citations.append(citation)

        return citations


class CitationVerifier:
    """Verify citations are valid and accurate."""

    @staticmethod
    def verify_document_exists(citation: Citation) -> bool:
        """Verify that document referenced in citation exists.

        Args:
            citation: Citation to verify

        Returns:
            True if document exists
        """
        from pathlib import Path

        try:
            path = Path(citation.path)
            exists = path.exists()

            if exists:
                logger.debug(f"Verified document exists: {citation.path}")
            else:
                logger.warning(f"Document not found: {citation.path}")

            return exists

        except Exception as e:
            logger.error(f"Failed to verify document existence: {e}")
            return False

    @staticmethod
    def verify_content_match(
        citation: Citation,
        answer_text: str,
        min_similarity: float = 0.3,
    ) -> bool:
        """Verify that citation content appears in answer.

        Args:
            citation: Citation to verify
            answer_text: Answer text to check against
            min_similarity: Minimum similarity threshold

        Returns:
            True if content matches
        """
        if not citation.snippet:
            logger.warning("Citation has no snippet for verification")
            return False

        # Simple substring match for now
        # In production, could use more sophisticated similarity matching
        snippet_lower = citation.snippet.lower()
        answer_lower = answer_text.lower()

        # Check if snippet words appear in answer
        snippet_words = set(snippet_lower.split())
        answer_words = set(answer_lower.split())

        if not snippet_words:
            return True

        overlap = len(snippet_words & answer_words)
        similarity = overlap / len(snippet_words)

        verified = similarity >= min_similarity

        if verified:
            logger.debug(
                f"Content match verified for {citation.title} (similarity: {similarity:.2f})"
            )
        else:
            logger.warning(
                f"Content match failed for {citation.title} (similarity: {similarity:.2f})"
            )

        return verified

    @staticmethod
    def verify_citation(
        citation: Citation,
        answer_text: str,
        verify_existence: bool = True,
        verify_content: bool = True,
    ) -> VerifiedCitation:
        """Verify a citation.

        Args:
            citation: Citation to verify
            answer_text: Answer text for content verification
            verify_existence: Whether to check document exists
            verify_content: Whether to check content matches

        Returns:
            VerifiedCitation with verification status
        """
        verified = True
        verification_method = ""

        if verify_existence:
            if not CitationVerifier.verify_document_exists(citation):
                verified = False
            verification_method = "document_exists"

        if verify_content and verified:
            if not CitationVerifier.verify_content_match(citation, answer_text):
                verified = False
            verification_method = "content_match"

        from datetime import datetime

        return VerifiedCitation(
            citation=citation,
            verified=verified,
            verification_method=verification_method,
            verification_timestamp=datetime.utcnow().isoformat(),
        )


class CitationFormatter:
    """Format citations for output."""

    @staticmethod
    def format_citations_markdown(citations: list[Citation]) -> str:
        """Format citations as markdown list.

        Args:
            citations: List of citations

        Returns:
            Markdown formatted citations
        """
        if not citations:
            return ""

        lines = ["## Citations\n"]
        for i, citation in enumerate(citations, 1):
            lines.append(f"{i}. {citation.to_markdown()}")

        return "\n".join(lines)

    @staticmethod
    def format_citations_html(citations: list[Citation]) -> str:
        """Format citations as HTML.

        Args:
            citations: List of citations

        Returns:
            HTML formatted citations
        """
        if not citations:
            return ""

        lines = ["<div class='citations'><h3>Citations</h3><ol>"]
        for citation in citations:
            lines.append(f"<li>{citation.to_html()}</li>")
        lines.append("</ol></div>")

        return "\n".join(lines)

    @staticmethod
    def format_answer_with_citations(
        answer: Answer,
        format_type: str = "markdown",
    ) -> str:
        """Format answer with citations.

        Args:
            answer: Answer with citations
            format_type: "markdown" or "html"

        Returns:
            Formatted answer with citations
        """
        output = answer.content + "\n\n"

        if answer.has_citations:
            if format_type == "html":
                output += CitationFormatter.format_citations_html(answer.citations)
            else:
                output += CitationFormatter.format_citations_markdown(answer.citations)

        return output

    @staticmethod
    def generate_citation_index(citations: list[Citation]) -> dict:
        """Generate index of citations by source.

        Args:
            citations: List of citations

        Returns:
            Dict indexed by document path
        """
        index = {}

        for citation in citations:
            path = citation.path
            if path not in index:
                index[path] = {
                    "title": citation.title,
                    "citations": [],
                }

            index[path]["citations"].append(
                {
                    "section": citation.section,
                    "snippet": citation.snippet,
                    "confidence": citation.confidence,
                }
            )

        return index
