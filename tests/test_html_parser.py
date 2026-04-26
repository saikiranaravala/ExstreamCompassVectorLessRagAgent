"""Tests for HTML parser."""

import pytest

from compass.indexer.html_parser import HTMLParser, ParsedHTML


class TestHTMLParser:
    """Test HTMLParser class."""

    def test_parse_simple_html(self):
        """Test parsing simple HTML."""
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Hello World</h1>
                <p>This is test content.</p>
            </body>
        </html>
        """
        result = HTMLParser.parse_string(html, "test.html")

        assert result is not None
        assert isinstance(result, ParsedHTML)
        assert result.title
        assert result.url == "test.html"
        assert "content" in result.text.lower() or "hello" in result.text.lower()

    def test_parse_html_with_scripts_and_styles(self):
        """Test that scripts and styles are removed."""
        html = """
        <html>
            <head>
                <title>Test</title>
                <style>body { color: red; }</style>
            </head>
            <body>
                <p>Visible content</p>
                <script>alert('hidden');</script>
            </body>
        </html>
        """
        result = HTMLParser.parse_string(html)

        assert result is not None
        assert "visible content" in result.text.lower()
        assert "alert" not in result.text.lower()
        assert "color" not in result.text.lower()

    def test_parse_html_with_complex_structure(self):
        """Test parsing HTML with complex structure."""
        html = """
        <html>
            <head><title>Documentation</title></head>
            <body>
                <nav>Navigation</nav>
                <main>
                    <article>
                        <h1>Article Title</h1>
                        <p>Paragraph 1</p>
                        <p>Paragraph 2</p>
                    </article>
                </main>
                <footer>Footer content</footer>
            </body>
        </html>
        """
        result = HTMLParser.parse_string(html, "doc.html")

        assert result is not None
        assert result.title
        assert result.url == "doc.html"
        assert len(result.text) > 0

    def test_parse_empty_html(self):
        """Test parsing empty HTML."""
        result = HTMLParser.parse_string("", "empty.html")

        assert result is not None
        assert result.url == "empty.html"

    def test_parse_malformed_html(self):
        """Test parsing malformed HTML."""
        html = "<html><body><p>Unclosed paragraph<div>Nested</p></div></body></html>"
        result = HTMLParser.parse_string(html)

        assert result is not None
        assert result.text

    def test_parse_html_with_entities(self):
        """Test parsing HTML with character entities."""
        html = """
        <html>
            <body>
                <p>Symbols: &lt; &gt; &amp; &quot;</p>
                <p>Accents: café, naïve</p>
            </body>
        </html>
        """
        result = HTMLParser.parse_string(html)

        assert result is not None
        assert len(result.text) > 0

    def test_parsed_html_dataclass(self):
        """Test ParsedHTML dataclass."""
        parsed = ParsedHTML(
            title="Test",
            url="test.html",
            content="<p>content</p>",
            text="content",
            html="<html></html>",
        )

        assert parsed.title == "Test"
        assert parsed.url == "test.html"
        assert parsed.content == "<p>content</p>"
        assert parsed.text == "content"
