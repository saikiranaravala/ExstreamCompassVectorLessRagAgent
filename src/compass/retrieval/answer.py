"""Answer generation: structured, cited explanations over retrieved passages."""

import logging
from typing import Optional

from compass.config import settings

logger = logging.getLogger(__name__)

try:
    from langsmith import traceable as _traceable
    from langsmith.wrappers import wrap_openai as _wrap_openai
except ImportError:  # pragma: no cover

    def _traceable(func=None, **kwargs):
        if func is not None:
            return func
        return lambda f: f

    def _wrap_openai(client):
        return client


VARIANT_LABELS = {
    "CloudNative": "Cloud Native (containerized/Kubernetes deployment)",
    "ServerBased": "Server Based (traditional on-premises deployment)",
}

SYSTEM_PROMPT = """You are Compass, an expert assistant for OpenText Exstream documentation.
The user works with the {variant_label} variant of the product.

Answer the user's question using ONLY the numbered documentation sources provided.

Format your answer as GitHub-flavored markdown:
1. Start with a direct 1-3 sentence answer to the question.
2. Then explain the relevant details — use short paragraphs, bullet points, or numbered
   steps (for procedures) as appropriate.
3. Cite sources inline with bracketed numbers, e.g. "… the Exstream engine [2]",
   matching the source numbers you were given. Every factual claim needs a citation.
4. If the sources only partially answer the question, answer what you can, then state
   clearly what is not covered and name the closest related topics from the sources.
5. Never invent features, menu paths, commands, or steps that are not in the sources."""


def build_sources(hits: list[dict]) -> str:
    """Format retrieval hits as a numbered source block for the prompt.

    Args:
        hits: dicts with keys title, path, passage

    Returns:
        Numbered sources string
    """
    blocks = []
    for i, hit in enumerate(hits, 1):
        blocks.append(f"[{i}] {hit['title']}\n(file: {hit['path']})\n{hit['passage']}")
    return "\n\n".join(blocks)


@_traceable(name="llm_generate_answer", run_type="llm")
def generate_answer(
    query: str,
    variant: str,
    hits: list[dict],
    model: Optional[str] = None,
) -> tuple[str, bool]:
    """Generate a structured, cited answer from retrieved passages.

    Args:
        query: User question
        variant: Documentation variant
        hits: Retrieval hits (title, path, passage)
        model: Override model name (defaults to settings.reasoning_model)

    Returns:
        (answer_markdown, used_llm) — used_llm is False when the extractive
        fallback was used (no API key or the LLM call failed).
    """
    if not hits:
        return (
            f"I could not find documentation matching **{query}** in the "
            f"{variant} docs. Try rephrasing with product terms (for example: "
            f"deployment, orchestration, Empower, Content Author, output queue, "
            f"engine, driver file).",
            False,
        )

    if not settings.openrouter_api_key:
        return _extractive_answer(query, hits), False

    system = SYSTEM_PROMPT.format(variant_label=VARIANT_LABELS.get(variant, variant))
    user = (
        f"Question: {query}\n\n"
        f"Documentation sources:\n\n{build_sources(hits)}"
    )

    try:
        from openai import OpenAI

        client = _wrap_openai(
            OpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
            )
        )
        response = client.chat.completions.create(
            model=model or settings.reasoning_model,
            max_tokens=1600,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        answer = (response.choices[0].message.content or "").strip()
        if answer:
            return answer, True
        logger.warning("LLM returned an empty answer; using extractive fallback")
    except Exception as e:
        logger.error(f"LLM answer generation failed: {e}")

    return _extractive_answer(query, hits), False


def _extractive_answer(query: str, hits: list[dict]) -> str:
    """Assemble a readable answer directly from the passages (no LLM)."""
    parts = [
        f"Here is what the documentation says about **{query}** "
        f"(live answer generation is unavailable right now):",
        "",
    ]
    for i, hit in enumerate(hits[:4], 1):
        parts.append(f"**{i}. {hit['title']}**")
        parts.append(hit["passage"])
        parts.append("")
    return "\n".join(parts).strip()
