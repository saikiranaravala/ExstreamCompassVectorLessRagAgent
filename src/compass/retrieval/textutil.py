"""Text utilities: HTML text extraction and tokenization."""

import logging
import re
from html.parser import HTMLParser as _StdHTMLParser

logger = logging.getLogger(__name__)

try:
    from selectolax.parser import HTMLParser as _SelectolaxParser

    _HAS_SELECTOLAX = True
except ImportError:  # pragma: no cover - depends on environment
    _HAS_SELECTOLAX = False

STOPWORDS = frozenset(
    """a an and are as at be but by can do does for from had has have how i if in into
    is it its of on or not no so such that the their then there these this to was we
    were what when where which who will with would you your""".split()
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_\-]*")
_WS_RE = re.compile(r"\s+")


def tokenize(text: str) -> list[str]:
    """Tokenize text for indexing/search: lowercase words, light plural folding.

    Args:
        text: Raw text

    Returns:
        List of normalized tokens (stopwords removed)
    """
    tokens = []
    for tok in _WORD_RE.findall(text.lower()):
        if len(tok) < 2 or tok in STOPWORDS:
            continue
        # Light plural folding: "engines" -> "engine", but keep "css", "process" safe-ish
        if len(tok) > 3 and tok.endswith("s") and not tok.endswith(("ss", "us", "is")):
            tok = tok[:-1]
        tokens.append(tok)
    return tokens


class _FallbackExtractor(_StdHTMLParser):
    """Stdlib HTML text extractor used when selectolax is unavailable."""

    _SKIP_TAGS = {"script", "style", "head", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        elif self._skip_depth == 0:
            self.text_parts.append(data)


def extract_html_text(html: str) -> tuple[str, str]:
    """Extract (title, body text) from an HTML document.

    Uses selectolax when installed (fast C parser); otherwise falls back to the
    standard library parser so the API works with minimal dependencies.

    Args:
        html: Raw HTML string

    Returns:
        Tuple of (title, whitespace-normalized body text)
    """
    if _HAS_SELECTOLAX:
        try:
            tree = _SelectolaxParser(html)
            title_node = tree.css_first("title")
            title = title_node.text(strip=True) if title_node else ""
            for node in tree.css("script, style, head, noscript, template"):
                node.decompose()
            body = tree.body
            text = body.text(separator=" ") if body else tree.text(separator=" ")
            return _WS_RE.sub(" ", title).strip(), _WS_RE.sub(" ", text).strip()
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"selectolax parse failed, using fallback: {e}")

    extractor = _FallbackExtractor()
    try:
        extractor.feed(html)
    except Exception as e:
        logger.debug(f"HTML parse error (continuing with partial text): {e}")
    title = _WS_RE.sub(" ", " ".join(extractor.title_parts)).strip()
    text = _WS_RE.sub(" ", " ".join(extractor.text_parts)).strip()
    return title, text
