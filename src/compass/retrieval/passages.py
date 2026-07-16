"""Query-relevant passage extraction.

Instead of sending the LLM the first N characters of a document (which is
usually navigation and preamble), slide a window over the text and return the
spans that actually contain the query terms.
"""

from compass.retrieval.textutil import tokenize

WINDOW_WORDS = 120
STRIDE_WORDS = 60
ADJACENCY_BONUS = 0.5


def best_passage(
    text: str,
    term_idf: dict[str, float],
    max_chars: int = 900,
) -> str:
    """Return the highest-scoring window of ``text`` for the given query terms.

    Args:
        text: Full document text
        term_idf: Query terms mapped to idf weights (from BM25Index.query_terms)
        max_chars: Truncation limit for the returned passage

    Returns:
        The best passage (falls back to the start of the document when no
        term matches — e.g. a title-only hit).
    """
    words = text.split()
    if not words:
        return ""
    if len(words) <= WINDOW_WORDS:
        return _clip(" ".join(words), max_chars)

    best_score, best_start = -1.0, 0
    for start in range(0, len(words) - WINDOW_WORDS + 1, STRIDE_WORDS):
        window = words[start : start + WINDOW_WORDS]
        tokens = tokenize(" ".join(window))
        if not tokens:
            continue
        seen: dict[str, int] = {}
        for t in tokens:
            if t in term_idf:
                seen[t] = seen.get(t, 0) + 1
        if not seen:
            continue
        # unique-term coverage dominates; repeats add a little
        score = sum(term_idf[t] * (1 + 0.15 * (n - 1)) for t, n in seen.items())
        # bonus when multiple distinct query terms co-occur (likely the topic)
        if len(seen) > 1:
            score += ADJACENCY_BONUS * len(seen)
        if score > best_score:
            best_score, best_start = score, start

    if best_score < 0:
        return _clip(" ".join(words[:WINDOW_WORDS]), max_chars)

    # widen slightly for context, then clip
    start = max(0, best_start - 15)
    passage = " ".join(words[start : best_start + WINDOW_WORDS + 25])
    prefix = "… " if start > 0 else ""
    return prefix + _clip(passage, max_chars)


def _clip(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text.rfind(" ", 0, max_chars)
    return text[: cut if cut > 0 else max_chars].rstrip() + " …"
