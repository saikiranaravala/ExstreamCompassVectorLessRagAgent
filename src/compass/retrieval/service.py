"""QueryService: the single orchestration point for answering queries.

Used by the API routes and by the agent tools, so both paths share one
corpus, one index, and one answering policy.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional

from compass.config import settings
from compass.guardrails import GuardrailPipeline
from compass.guardrails.policy import Category, Decision
from compass.retrieval.answer import generate_answer
from compass.retrieval.bm25 import BM25Index
from compass.retrieval.corpus import CorpusStore
from compass.retrieval.passages import best_passage

logger = logging.getLogger(__name__)

DEFAULT_VARIANTS = ("CloudNative", "ServerBased")
SEARCH_LIMIT = 8
ANSWER_SOURCES = 6
PASSAGE_CHARS = 900
CITATION_CHARS = 500


def _find_project_root() -> Path:
    """Locate the repository root (the folder containing docs/)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "docs").is_dir():
            return parent
    return Path.cwd()


class QueryService:
    """Thread-safe, lazily-initialized retrieval + answering service."""

    def __init__(
        self,
        docs_root: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        guardrails: Optional[GuardrailPipeline] = None,
    ):
        root = _find_project_root()
        self.docs_root = Path(docs_root) if docs_root else root / settings.docs_root
        self.cache_dir = Path(cache_dir) if cache_dir else root / settings.atlas_path
        self.corpus = CorpusStore(self.docs_root, self.cache_dir)
        self._indexes: dict[str, BM25Index] = {}
        self._locks: dict[str, threading.Lock] = {v: threading.Lock() for v in DEFAULT_VARIANTS}
        self._global_lock = threading.Lock()
        # Shared guardrail pipeline (rate limit + input + output guards).
        self.guardrails = guardrails or GuardrailPipeline()

    # ------------------------------------------------------------- index --

    def get_index(self, variant: str, rebuild: bool = False) -> BM25Index:
        """Get (building if necessary) the BM25 index for a variant."""
        if not rebuild and variant in self._indexes:
            return self._indexes[variant]
        with self._global_lock:
            lock = self._locks.setdefault(variant, threading.Lock())
        with lock:
            if rebuild or variant not in self._indexes:
                docs = self.corpus.load(variant, rebuild=rebuild)
                self._indexes[variant] = BM25Index(docs)
        return self._indexes[variant]

    def warmup(self, variants: tuple[str, ...] = DEFAULT_VARIANTS) -> None:
        """Build all indexes (call from a background thread at startup)."""
        for variant in variants:
            try:
                self.get_index(variant)
            except Exception as e:
                logger.error(f"Warmup failed for {variant}: {e}")

    def status(self) -> dict:
        """Index status for health/diagnostics endpoints."""
        return {
            "docs_root": str(self.docs_root),
            "indexes": {v: idx.n_docs for v, idx in self._indexes.items()},
        }

    # ------------------------------------------------------------ search --

    def search(self, query: str, variant: str, limit: int = SEARCH_LIMIT) -> list[dict]:
        """Full-corpus BM25 search with query-relevant passages.

        Returns:
            Hits as dicts: {doc_id, title, path, score, passage}
        """
        index = self.get_index(variant)
        terms = index.query_terms(query)
        hits = []
        for scored in index.search(query, limit=limit):
            hits.append(
                {
                    "doc_id": scored.doc.doc_id,
                    "title": scored.doc.title,
                    "path": scored.doc.path,
                    "score": round(scored.score, 3),
                    "passage": best_passage(scored.doc.text, terms, max_chars=PASSAGE_CHARS),
                }
            )
        return hits

    # ------------------------------------------------------------- query --

    def query(self, query: str, variant: str, identity: str = "anonymous") -> dict:
        """Answer a question: guardrails -> search -> passages -> cited answer.

        Args:
            query: User question
            variant: Documentation variant
            identity: Caller identity for rate limiting (user id / demo / ip)

        Returns:
            dict with answer, citations, tool_calls, trace, model info, and a
            ``guardrail`` block describing the input/output decision.
        """
        started = time.time()
        trace: list[str] = []

        # -- input guardrail (rate limit + validation + injection/PII) ----------
        pre = self.guardrails.check_request(query, identity=identity)
        if pre.blocked:
            trace.append(f"Guardrail blocked request: {pre.category.value}")
            resp = self.guardrails.refusal_response(pre, variant)
            resp["processing_time"] = round(time.time() - started, 3)
            resp["trace"] = trace + resp["trace"]
            return resp
        safe_query = pre.sanitized_text or query
        if pre.decision == Decision.SANITIZE:
            trace.append(f"Guardrail sanitized query: {pre.reason}")

        index = self.get_index(variant)
        trace.append(f"Index ready: {index.n_docs} documents ({variant})")

        hits = self.search(safe_query, variant, limit=SEARCH_LIMIT)
        trace.append(f"BM25 search returned {len(hits)} hits")
        top_score = hits[0]["score"] if hits else 0.0

        sources = hits[:ANSWER_SOURCES]
        answer, used_llm = generate_answer(safe_query, variant, sources)
        trace.append(
            "Answer generated by "
            + (settings.reasoning_model if used_llm else "extractive fallback")
        )

        # -- output guardrail (grounding / leakage / secrets) -------------------
        post = self.guardrails.check_response(answer, sources, variant, top_score)
        answer = post.sanitized_text or answer
        low_confidence = post.category == Category.LOW_CONFIDENCE
        if post.category in (Category.LOW_CONFIDENCE, Category.LEAKED, Category.UNGROUNDED):
            trace.append(f"Guardrail output check: {post.category.value} ({post.reason})")
        if low_confidence:
            from compass.guardrails.policy import message_for

            disclaimer = message_for(Category.LOW_CONFIDENCE, self.guardrails.cfg, variant=variant)
            answer = f"> {disclaimer}\n\n{answer}"

        citations = [
            {
                "doc_id": h["doc_id"],
                "title": h["title"],
                "path": h["path"],
                "content": h["passage"][:CITATION_CHARS],
            }
            for h in sources
        ]

        # merge input+output guardrail metadata for audit/telemetry
        guardrail_info = {"input": pre.to_audit(), "output": post.to_audit()}

        return {
            "answer": answer,
            "citations": citations,
            "tool_calls": 1 + len(sources),  # 1 search + N passage reads
            "variant": variant,
            "model": settings.reasoning_model if used_llm else None,
            "trace": trace,
            "processing_time": round(time.time() - started, 3),
            "guardrail": guardrail_info,
        }
