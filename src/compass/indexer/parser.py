"""Document parser for HTML, PDF, and scanned content.

Handles:
- HTML parsing (selectolax + readability-lxml)
- PDF text extraction (pypdf)
- PDF table extraction (pdfplumber)
- OCR fallback for scanned documents (pytesseract)
"""
