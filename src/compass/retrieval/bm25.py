"""Pure-Python BM25 index over the parsed corpus.

No native dependencies: builds in a few seconds for ~4,000 documents and is
fast enough for interactive queries. Title matches get an additional weighted
score so topic pages rank above passing mentions.
"""

import logging
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass

from compass.retrieval.corpus import DocRecord
from compass.retrieval.textutil import tokenize

logger = logging.getLogger(__name__)

K1 = 1.5
B = 0.75
TITLE_WEIGHT = 1.8


@dataclass
class ScoredDoc:
    """A search hit."""

    doc: DocRecord
    score: float


class BM25Index:
    """In-memory BM25 index with a weighted title field."""

    def __init__(self, docs: list[DocRecord]):
        started = time.time()
        self.docs = docs
        self.doc_len: list[int] = []
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.title_postings: dict[str, list[tuple[int, int]]] = defaultdict(list)

        for idx, doc in enumerate(docs):
            body_tokens = tokenize(doc.text)
            self.doc_len.append(len(body_tokens))
            for term, tf in Counter(body_tokens).items():
                self.postings[term].append((idx, tf))
            for term, tf in Counter(tokenize(doc.title)).items():
                self.title_postings[term].append((idx, tf))

        self.n_docs = len(docs)
        self.avgdl = (sum(self.doc_len) / self.n_docs) if self.n_docs else 0.0
        logger.info(
            f"BM25 index built: {self.n_docs} docs, {len(self.postings)} terms "
            f"in {time.time() - started:.1f}s"
        )

    def idf(self, term: str) -> float:
        df = len(self.postings.get(term, ()))
        if df == 0:
            return 0.0
        return math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))

    def query_terms(self, query: str) -> dict[str, float]:
        """Unique query terms with their idf (terms unseen in corpus get 0)."""
        return {t: self.idf(t) for t in dict.fromkeys(tokenize(query))}

    def search(self, query: str, limit: int = 8) -> list[ScoredDoc]:
        """Rank documents for a query.

        Args:
            query: Free-text query
            limit: Maximum hits to return

        Returns:
            ScoredDoc list, highest score first (empty if nothing matches)
        """
        terms = self.query_terms(query)
        if not self.n_docs or not terms:
            return []

        scores: dict[int, float] = defaultdict(float)
        for term, idf in terms.items():
            if idf <= 0:
                continue
            for idx, tf in self.postings.get(term, ()):
                dl = self.doc_len[idx] or 1
                denom = tf + K1 * (1 - B + B * dl / self.avgdl)
                scores[idx] += idf * (tf * (K1 + 1)) / denom
            for idx, tf in self.title_postings.get(term, ()):
                scores[idx] += TITLE_WEIGHT * idf * (tf * (K1 + 1)) / (tf + K1)

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [ScoredDoc(doc=self.docs[idx], score=score) for idx, score in ranked]
