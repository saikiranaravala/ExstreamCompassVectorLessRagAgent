"""HTML parser for documentation files using selectolax and readability-lxml."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from readability import Document
from selectolax.parser import HTMLParser as SelectolaxParser

logger = logging.getLogger(__name__)


@dataclass
class ParsedHTML:
    """Result of HTML parsing."""

    title: str
    url: str
    content: str
    text: str
    html: str


class HTMLParser:
    """Parse HTML documentation files."""

    @staticmethod
    def parse_file(file_path: Path) -> Optional[ParsedHTML]:
        """Parse an HTML file.

        Args:
            file_path: Path to HTML file

        Returns:
            ParsedHTML with extracted content, or None if parsing fails
        """
        try:
            html_content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None

        return HTMLParser.parse_string(html_content, str(file_path))

    @staticmethod
    def parse_string(html: str, url: str = "") -> Optional[ParsedHTML]:
        """Parse HTML string.

        Args:
            html: HTML content as string
            url: Document URL/path for reference

        Returns:
            ParsedHTML with extracted content, or None if parsing fails
        """
        try:
            doc = Document(html)
            title = doc.short_title() or ""
            content = doc.summary() or ""

            parser = SelectolaxParser(html)
            text_content = HTMLParser._extract_text(parser)

            return ParsedHTML(
                title=title,
                url=url,
                content=content,
                text=text_content,
                html=html,
            )
        except Exception as e:
            logger.error(f"Failed to parse HTML from {url}: {e}")
            return None

    @staticmethod
    def _extract_text(parser: SelectolaxParser) -> str:
        """Extract clean text from parsed HTML.

        Args:
            parser: selectolax HTMLParser instance

        Returns:
            Extracted text content
        """
        body = parser.select("body")
        if not body:
            return ""

        body_elem = body[0]

        # Remove script and style tags
        for elem in body_elem.select("script, style"):
            elem.decompose()

        # Get text content
        text = body_elem.text()
        # Clean up whitespace
        text = " ".join(text.split())

        return text
