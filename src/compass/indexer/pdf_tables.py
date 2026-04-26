"""PDF table extraction using pdfplumber."""

import io
import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Extracted table from PDF."""

    page_num: int
    table_num: int
    rows: list[list[str]]
    bbox: tuple[float, float, float, float]

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "page": self.page_num,
            "table_index": self.table_num,
            "rows": self.rows,
            "bbox": self.bbox,
        }

    def to_markdown(self) -> str:
        """Convert to markdown table format."""
        if not self.rows:
            return ""

        lines = []
        for i, row in enumerate(self.rows):
            lines.append("| " + " | ".join(str(cell or "") for cell in row) + " |")
            if i == 0 and len(self.rows) > 1:
                lines.append("|" + "|".join(["---"] * len(row)) + "|")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Convert to JSON representation."""
        return json.dumps(self.to_dict(), indent=2)


class PDFTableExtractor:
    """Extract tables from PDF documents."""

    @staticmethod
    def extract_from_bytes(pdf_bytes: bytes) -> list[ExtractedTable]:
        """Extract all tables from PDF bytes.

        Args:
            pdf_bytes: PDF content as bytes

        Returns:
            List of ExtractedTable objects
        """
        tables = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = PDFTableExtractor._extract_page_tables(page, page_num)
                    tables.extend(page_tables)
        except Exception as e:
            logger.error(f"Failed to extract tables from PDF: {e}")

        return tables

    @staticmethod
    def extract_from_file(file_path: str) -> list[ExtractedTable]:
        """Extract all tables from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            List of ExtractedTable objects
        """
        try:
            with open(file_path, "rb") as f:
                return PDFTableExtractor.extract_from_bytes(f.read())
        except (FileNotFoundError, IOError) as e:
            logger.warning(f"Failed to read PDF file {file_path}: {e}")
            return []

    @staticmethod
    def _extract_page_tables(page: Any, page_num: int) -> list[ExtractedTable]:
        """Extract tables from a single PDF page.

        Args:
            page: pdfplumber page object
            page_num: Page number (1-indexed)

        Returns:
            List of ExtractedTable objects from this page
        """
        page_tables = []
        try:
            tables = page.extract_tables()
            if not tables:
                return page_tables

            for table_idx, table in enumerate(tables, 1):
                if not table:
                    continue

                # Convert cells to strings and handle None values
                rows = [
                    [str(cell or "") for cell in row] for row in table
                ]

                # Try to get table bounding box
                try:
                    bbox = page.find_tables()[table_idx - 1].bbox
                except (IndexError, AttributeError):
                    bbox = (0.0, 0.0, 0.0, 0.0)

                extracted = ExtractedTable(
                    page_num=page_num,
                    table_num=table_idx,
                    rows=rows,
                    bbox=bbox,
                )
                page_tables.append(extracted)

        except Exception as e:
            logger.warning(f"Failed to extract tables from page {page_num}: {e}")

        return page_tables

    @staticmethod
    def extract_as_markdown(pdf_bytes: bytes) -> str:
        """Extract all tables as markdown.

        Args:
            pdf_bytes: PDF content as bytes

        Returns:
            Markdown formatted tables with page annotations
        """
        tables = PDFTableExtractor.extract_from_bytes(pdf_bytes)
        if not tables:
            return ""

        output = []
        current_page = None

        for table in tables:
            if table.page_num != current_page:
                output.append(f"\n## Page {table.page_num}\n")
                current_page = table.page_num

            output.append(f"### Table {table.table_num}\n")
            output.append(table.to_markdown())
            output.append("\n")

        return "\n".join(output)

    @staticmethod
    def extract_as_json(pdf_bytes: bytes) -> str:
        """Extract all tables as JSON.

        Args:
            pdf_bytes: PDF content as bytes

        Returns:
            JSON formatted tables
        """
        tables = PDFTableExtractor.extract_from_bytes(pdf_bytes)
        return json.dumps([table.to_dict() for table in tables], indent=2)

    @staticmethod
    def get_table_count(pdf_bytes: bytes) -> int:
        """Count total tables in PDF.

        Args:
            pdf_bytes: PDF content as bytes

        Returns:
            Total number of tables
        """
        tables = PDFTableExtractor.extract_from_bytes(pdf_bytes)
        return len(tables)
