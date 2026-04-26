"""Tests for PDF parser."""

import io

import pytest

from compass.indexer.pdf_parser import PDFParser, ParsedPDF


class TestPDFParser:
    """Test PDFParser class."""

    @pytest.fixture
    def sample_pdf_bytes(self):
        """Create a minimal valid PDF for testing."""
        # Minimal PDF structure
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Hello PDF) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000273 00000 n
0000000363 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
456
%%EOF
"""
        return pdf_content

    def test_parse_minimal_pdf(self, sample_pdf_bytes):
        """Test parsing a minimal PDF."""
        result = PDFParser.parse_bytes(sample_pdf_bytes, "test.pdf")

        assert result is not None
        assert isinstance(result, ParsedPDF)
        assert result.url == "test.pdf"
        assert result.pages == 1

    def test_parse_pdf_metadata(self, sample_pdf_bytes):
        """Test PDF metadata extraction."""
        result = PDFParser.parse_bytes(sample_pdf_bytes, "test.pdf")

        assert result is not None
        assert isinstance(result.metadata, dict)
        assert "title" in result.metadata
        assert "author" in result.metadata

    def test_parse_pdf_with_empty_bytes(self):
        """Test parsing empty PDF bytes."""
        result = PDFParser.parse_bytes(b"", "empty.pdf")

        # Should return None for invalid PDF
        assert result is None

    def test_parse_pdf_with_invalid_data(self):
        """Test parsing invalid PDF data."""
        result = PDFParser.parse_bytes(b"Not a PDF at all", "invalid.pdf")

        assert result is None

    def test_parsed_pdf_dataclass(self):
        """Test ParsedPDF dataclass."""
        parsed = ParsedPDF(
            title="Test PDF",
            url="test.pdf",
            text="Sample text content",
            pages=5,
            metadata={"author": "Test Author"},
        )

        assert parsed.title == "Test PDF"
        assert parsed.url == "test.pdf"
        assert parsed.text == "Sample text content"
        assert parsed.pages == 5
        assert parsed.metadata["author"] == "Test Author"

    def test_parse_bytes_with_metadata_extraction(self, sample_pdf_bytes):
        """Test that metadata is properly extracted."""
        result = PDFParser.parse_bytes(sample_pdf_bytes)

        assert result is not None
        assert result.metadata is not None
        assert isinstance(result.metadata, dict)

    def test_parse_pdf_error_handling(self):
        """Test error handling for corrupted PDF."""
        corrupted_pdf = b"%PDF-1.4\nThis is corrupted"
        result = PDFParser.parse_bytes(corrupted_pdf, "corrupted.pdf")

        # Should handle gracefully and return None
        assert result is None or (result and result.text == "")
