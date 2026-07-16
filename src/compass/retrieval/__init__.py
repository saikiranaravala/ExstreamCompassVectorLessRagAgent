"""Retrieval layer: corpus loading, BM25 search, passage extraction, answering.

This package is dependency-light by design: it prefers ``selectolax`` for HTML
parsing when available but falls back to the standard library, and implements
BM25 in pure Python so it runs anywhere the API runs (including Render's free
tier, which installs only ``requirements-render.txt``).
"""

from compass.retrieval.service import QueryService

__all__ = ["QueryService"]
