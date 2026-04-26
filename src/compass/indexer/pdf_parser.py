"""PDF parser for documentation files using pypdf and pdfplumber."""

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pdfplumber
from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class ParsedPDF:
    """Result of PDF parsing."""

    title: str
    url: str
    text: str
    pages: int
    metadata: dict


class PDFParser:
    """Parse PDF documentation files."""

    @staticmethod
    def parse_file(file_path: Path) -> Optional[ParsedPDF]:
        """Parse a PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            ParsedPDF with extracted content, or None if parsing fails
        """
        try:
            with open(file_path, "rb") as f:
                return PDFParser.parse_bytes(f.read(), str(file_path))
        except (FileNotFoundError, IOError) as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None

    @staticmethod
    def parse_bytes(pdf_bytes: bytes, url: str = "") -> Optional[ParsedPDF]:
        """Parse PDF from bytes.

        Args:
            pdf_bytes: PDF content as bytes
            url: Document URL/path for reference

        Returns:
            ParsedPDF with extracted content, or None if parsing fails
        """
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            num_pages = len(reader.pages)

            # Extract metadata
            metadata = PDFParser._extract_metadata(reader)
            title = metadata.get("title", "")

            # Extract text using pdfplumber for better results
            text = PDFParser._extract_text_pdfplumber(pdf_bytes)

            return ParsedPDF(
                title=title,
                url=url,
                text=text,
                pages=num_pages,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to parse PDF from {url}: {e}")
            return None

    @staticmethod
    def _extract_metadata(reader: PdfReader) -> dict:
        """Extract metadata from PDF.

        Args:
            reader: PdfReader instance

        Returns:
            Dictionary of metadata
        """
        metadata = reader.metadata or {}
        return {
            "title": metadata.get("/Title", ""),
            "author": metadata.get("/Author", ""),
            "subject": metadata.get("/Subject", ""),
            "creator": metadata.get("/Creator", ""),
            "producer": metadata.get("/Producer", ""),
        }

    @staticmethod
    def _extract_text_pdfplumber(pdf_bytes: bytes) -> str:
        """Extract text using pdfplumber for better accuracy.

        Args:
            pdf_bytes: PDF content as bytes

        Returns:
            Extracted text content
        """
        try:
            text_parts = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed, falling back: {e}")
            return PDFParser._extract_text_pypdf(pdf_bytes)

    @staticmethod
    def _extract_text_pypdf(pdf_bytes: bytes) -> str:
        """Fallback text extraction using pypdf.

        Args:
            pdf_bytes: PDF content as bytes

        Returns:
            Extracted text content
        """
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"pypdf extraction also failed: {e}")
            return ""
