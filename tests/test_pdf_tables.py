"""Tests for PDF table extraction."""

import json

import pytest

from compass.indexer.pdf_tables import ExtractedTable, PDFTableExtractor


class TestExtractedTable:
    """Test ExtractedTable dataclass."""

    def test_extracted_table_initialization(self):
        """Test creating an ExtractedTable."""
        rows = [
            ["Header1", "Header2"],
            ["Value1", "Value2"],
        ]
        table = ExtractedTable(
            page_num=1,
            table_num=1,
            rows=rows,
            bbox=(0.0, 100.0, 200.0, 300.0),
        )

        assert table.page_num == 1
        assert table.table_num == 1
        assert table.rows == rows
        assert table.bbox == (0.0, 100.0, 200.0, 300.0)

    def test_to_dict(self):
        """Test converting table to dictionary."""
        rows = [["A", "B"], ["C", "D"]]
        table = ExtractedTable(
            page_num=2,
            table_num=1,
            rows=rows,
            bbox=(0.0, 0.0, 100.0, 100.0),
        )

        result = table.to_dict()
        assert result["page"] == 2
        assert result["table_index"] == 1
        assert result["rows"] == rows
        assert result["bbox"] == (0.0, 0.0, 100.0, 100.0)

    def test_to_markdown(self):
        """Test converting table to markdown."""
        rows = [
            ["Name", "Age"],
            ["Alice", "30"],
            ["Bob", "25"],
        ]
        table = ExtractedTable(
            page_num=1,
            table_num=1,
            rows=rows,
            bbox=(0.0, 0.0, 100.0, 100.0),
        )

        markdown = table.to_markdown()
        assert "| Name | Age |" in markdown
        assert "| --- | --- |" in markdown
        assert "| Alice | 30 |" in markdown
        assert "| Bob | 25 |" in markdown

    def test_to_markdown_with_none_values(self):
        """Test markdown conversion handles None values."""
        rows = [
            ["A", "B"],
            ["C", None],
        ]
        table = ExtractedTable(
            page_num=1,
            table_num=1,
            rows=rows,
            bbox=(0.0, 0.0, 100.0, 100.0),
        )

        markdown = table.to_markdown()
        assert "| C |  |" in markdown

    def test_to_json(self):
        """Test converting table to JSON."""
        rows = [["A", "B"]]
        table = ExtractedTable(
            page_num=1,
            table_num=1,
            rows=rows,
            bbox=(0.0, 0.0, 100.0, 100.0),
        )

        json_str = table.to_json()
        parsed = json.loads(json_str)
        assert parsed["page"] == 1
        assert parsed["table_index"] == 1
        assert parsed["rows"] == rows


class TestPDFTableExtractor:
    """Test PDFTableExtractor class."""

    def test_extract_from_empty_bytes(self):
        """Test extracting tables from empty PDF bytes."""
        tables = PDFTableExtractor.extract_from_bytes(b"")
        assert tables == []

    def test_extract_from_invalid_bytes(self):
        """Test extracting tables from invalid PDF data."""
        tables = PDFTableExtractor.extract_from_bytes(b"Not a PDF")
        assert tables == []

    def test_extract_as_markdown_empty(self):
        """Test markdown extraction from empty PDF."""
        markdown = PDFTableExtractor.extract_as_markdown(b"")
        assert markdown == ""

    def test_extract_as_json_empty(self):
        """Test JSON extraction from empty PDF."""
        json_str = PDFTableExtractor.extract_as_json(b"")
        parsed = json.loads(json_str)
        assert parsed == []

    def test_get_table_count_empty(self):
        """Test table count from empty PDF."""
        count = PDFTableExtractor.get_table_count(b"")
        assert count == 0

    def test_extract_as_json_structure(self):
        """Test JSON structure is valid."""
        json_str = PDFTableExtractor.extract_as_json(b"")
        # Should be valid JSON array
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)

    def test_extracted_table_with_multiple_rows(self):
        """Test table with multiple rows."""
        rows = [
            ["H1", "H2", "H3"],
            ["A1", "A2", "A3"],
            ["B1", "B2", "B3"],
        ]
        table = ExtractedTable(
            page_num=1,
            table_num=1,
            rows=rows,
            bbox=(0.0, 0.0, 100.0, 100.0),
        )

        assert len(table.rows) == 3
        assert len(table.rows[0]) == 3

    def test_extracted_table_empty_rows(self):
        """Test handling of empty row list."""
        table = ExtractedTable(
            page_num=1,
            table_num=1,
            rows=[],
            bbox=(0.0, 0.0, 100.0, 100.0),
        )

        markdown = table.to_markdown()
        assert markdown == ""

    def test_extracted_table_with_special_chars(self):
        """Test table with special characters."""
        rows = [
            ["Name", "Description"],
            ["Item|A", "Value & Special"],
            ["Item<B>", "Value\"Quote"],
        ]
        table = ExtractedTable(
            page_num=1,
            table_num=1,
            rows=rows,
            bbox=(0.0, 0.0, 100.0, 100.0),
        )

        markdown = table.to_markdown()
        assert "Item|A" in markdown
        assert "Value & Special" in markdown
