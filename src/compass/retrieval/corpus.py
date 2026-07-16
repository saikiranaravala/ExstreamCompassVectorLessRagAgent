"""Corpus loading: scan, parse, and cache the documentation tree per variant."""

import gzip
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from compass.retrieval.textutil import extract_html_text

logger = logging.getLogger(__name__)

CACHE_VERSION = 1

# Folder names (lowercased) that hold viewer chrome, not documentation content.
SKIP_DIRS = {
    "skin",
    "skins",
    "data",
    "stylesheets",
    "scripts",
    "images",
    "image",
    "fonts",
    "js",
    "css",
    "template",
    "templates",
}

MIN_WORDS = 15  # drop navigation shells / empty frames
MAX_TEXT_CHARS = 60_000  # cap pathological documents


@dataclass
class DocRecord:
    """A parsed documentation file."""

    doc_id: str  # relative path from docs root (posix), unique
    variant: str
    path: str  # same as doc_id; kept explicit for API responses
    title: str
    text: str


class CorpusStore:
    """Loads and caches parsed documentation per variant.

    The first load walks ``docs/{variant}/HTML`` recursively, extracts text from
    every ``.htm``/``.html`` file, and writes a gzip JSON cache into
    ``.atlas/``. Subsequent loads read the cache (seconds instead of minutes).
    """

    def __init__(self, docs_root: Path, cache_dir: Path):
        self.docs_root = Path(docs_root)
        self.cache_dir = Path(cache_dir)

    def cache_path(self, variant: str) -> Path:
        return self.cache_dir / f"corpus_{variant}.json.gz"

    def load(self, variant: str, rebuild: bool = False) -> list[DocRecord]:
        """Load the corpus for a variant, building the cache if needed.

        Args:
            variant: "CloudNative" or "ServerBased" (any top-level docs folder)
            rebuild: Force a re-scan even if a cache exists

        Returns:
            List of DocRecord (possibly empty if the variant folder is missing)
        """
        cache_file = self.cache_path(variant)
        if not rebuild and cache_file.exists():
            try:
                with gzip.open(cache_file, "rt", encoding="utf-8") as f:
                    payload = json.load(f)
                if payload.get("version") == CACHE_VERSION:
                    docs = [DocRecord(variant=variant, **d) for d in payload["docs"]]
                    logger.info(f"Corpus cache hit: {variant} ({len(docs)} docs)")
                    return docs
                logger.info(f"Corpus cache version mismatch for {variant}; rebuilding")
            except Exception as e:
                logger.warning(f"Corpus cache unreadable for {variant} ({e}); rebuilding")

        docs = self._build(variant)
        self._write_cache(variant, docs)
        return docs

    def _iter_files(self, variant: str):
        html_root = self.docs_root / variant / "HTML"
        if not html_root.exists():
            logger.warning(f"No HTML docs found at {html_root}")
            return
        for path in sorted(html_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in (".htm", ".html"):
                continue
            rel_parts = {p.lower() for p in path.relative_to(html_root).parts[:-1]}
            if rel_parts & SKIP_DIRS:
                continue
            yield path

    def _build(self, variant: str) -> list[DocRecord]:
        started = time.time()
        docs: list[DocRecord] = []
        scanned = 0
        for path in self._iter_files(variant):
            scanned += 1
            try:
                html = path.read_text(encoding="utf-8", errors="ignore")
            except OSError as e:
                logger.debug(f"Unreadable file {path}: {e}")
                continue
            title, text = extract_html_text(html)
            if len(text.split()) < MIN_WORDS:
                continue
            rel = path.relative_to(self.docs_root).as_posix()
            docs.append(
                DocRecord(
                    doc_id=rel,
                    variant=variant,
                    path=rel,
                    title=title or path.stem,
                    text=text[:MAX_TEXT_CHARS],
                )
            )
        logger.info(
            f"Corpus built: {variant} — {len(docs)} docs kept of {scanned} files "
            f"in {time.time() - started:.1f}s"
        )
        return docs

    def _write_cache(self, variant: str, docs: list[DocRecord]) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": CACHE_VERSION,
                "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "docs": [
                    {"doc_id": d.doc_id, "path": d.path, "title": d.title, "text": d.text}
                    for d in docs
                ],
            }
            tmp = self.cache_path(variant).with_suffix(".tmp")
            with gzip.open(tmp, "wt", encoding="utf-8") as f:
                json.dump(payload, f)
            tmp.replace(self.cache_path(variant))
            logger.info(f"Corpus cache written: {self.cache_path(variant)}")
        except Exception as e:
            logger.warning(f"Could not write corpus cache for {variant}: {e}")

    def get_document(self, variant: str, rel_path: str) -> Optional[DocRecord]:
        """Parse a single document on demand (used by the read_html tool)."""
        candidate = (self.docs_root / rel_path).resolve()
        try:
            candidate.relative_to(self.docs_root.resolve() / variant)
        except ValueError:
            return None  # variant isolation: refuse paths outside the variant subtree
        if not candidate.is_file():
            return None
        html = candidate.read_text(encoding="utf-8", errors="ignore")
        title, text = extract_html_text(html)
        rel = candidate.relative_to(self.docs_root.resolve()).as_posix()
        return DocRecord(
            doc_id=rel, variant=variant, path=rel, title=title or candidate.stem, text=text
        )
