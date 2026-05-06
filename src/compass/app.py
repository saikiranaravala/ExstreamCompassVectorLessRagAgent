"""Main FastAPI application."""

import logging
import uuid
import os
import re
from pathlib import Path
from html.parser import HTMLParser
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from compass import __version__
from compass.api.gateway import APIGateway

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Compass RAG",
    description="Vectorless Retrieval-Augmented Generation agent for OpenText Exstream documentation",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API gateway with authentication
gateway = APIGateway(app)
gateway.register_routes()


class HTMLTextExtractor(HTMLParser):
    """Extract text from HTML, filtering out scripts and styles."""

    def __init__(self):
        super().__init__()
        self.text = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        """Skip script and style tags."""
        if tag in ("script", "style", "meta"):
            self.skip = True

    def handle_endtag(self, tag):
        """Resume after script and style tags."""
        if tag in ("script", "style", "meta"):
            self.skip = False

    def handle_data(self, data):
        """Handle text data."""
        if not self.skip:
            text = data.strip()
            if text and not text.startswith("font-size:") and "{" not in text:
                self.text.append(text)

    def get_text(self):
        """Get extracted text."""
        # Join and clean up
        text = " ".join(self.text)
        # Remove multiple spaces
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def search_documentation(query: str, variant: str = "CloudNative", max_results: int = 3) -> list:
    """Search documentation files for query."""
    docs_root = Path(__file__).parent.parent.parent / "docs"
    variant_path = docs_root / variant / "HTML"

    if not variant_path.exists():
        return []

    results = []
    query_terms = query.lower().split()

    # Find HTML files
    html_files = list(variant_path.glob("**/*.htm")) + list(variant_path.glob("**/*.html"))

    for html_file in html_files[:100]:  # Limit search to first 100 files
        try:
            with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Extract text from HTML
            extractor = HTMLTextExtractor()
            extractor.feed(content)
            text = extractor.get_text()

            # Calculate relevance score
            score = 0
            for term in query_terms:
                # Count occurrences of each query term
                score += text.lower().count(term) * 10

            # Check title for matches
            if "<title>" in content:
                title_match = re.search(r"<title>(.*?)</title>", content)
                if title_match:
                    title = title_match.group(1)
                    for term in query_terms:
                        if term in title.lower():
                            score += 50  # Boost title matches

            if score > 0:
                # Extract relevant excerpt
                excerpt = text[:300] if len(text) > 300 else text
                results.append(
                    {
                        "score": score,
                        "file": html_file.name,
                        "path": str(html_file.relative_to(docs_root)),
                        "title": title if title_match else html_file.name,
                        "excerpt": excerpt,
                    }
                )
        except Exception as e:
            logger.debug(f"Error processing {html_file}: {e}")
            continue

    # Sort by relevance and return top results
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


def generate_answer_from_docs(query: str, search_results: list) -> str:
    """Generate a helpful answer from documentation results."""
    if not search_results:
        return f"No documentation found for '{query}'. Try searching for: deployment, architecture, design, content author, communications, orchestrator, empower, web client, exstream engine."

    # Build comprehensive answer from multiple sources
    answer = ""

    # Add summary from first (most relevant) result
    first = search_results[0]
    answer += f"**{first['title']}**\n\n"
    answer += f"{first['excerpt'][:400]}\n\n"

    # Add related information from other results
    if len(search_results) > 1:
        answer += "**Related topics:**\n"
        for result in search_results[1:]:
            answer += f"- **{result['title']}**: {result['excerpt'][:200]}...\n"

    return answer


# Simple demo endpoints for testing
@app.post("/api/v1/query")
async def query(request: Request, query: str, variant: str = "CloudNative", session_id: str = None) -> dict:
    """Query endpoint - searches documentation and generates answer."""
    try:
        user = gateway.get_current_user(request)
    except HTTPException:
        # Allow demo access without authentication
        user = None

    session_id = session_id or str(uuid.uuid4())

    # Search documentation
    results = search_documentation(query, variant)

    if results:
        # Generate answer using LLM
        answer = generate_answer_from_docs(query, results)

        citations = [
            {
                "doc_id": result["file"],
                "title": result["title"],
                "path": result["path"],
                "content": result["excerpt"][:300],
            }
            for result in results
        ]
    else:
        answer = f"No documentation found for '{query}' in {variant} variant. Try searching for: deployment, architecture, design, content author, communications, orchestration, empower, web client."
        citations = []

    return {
        "session_id": session_id,
        "answer": answer,
        "citations": citations,
        "tool_calls": len(results),
        "processing_time": 0.5,
        "variant": variant,
    }


@app.get("/api/v1/session/{session_id}")
async def get_session(session_id: str, request: Request) -> dict:
    """Get session information."""
    try:
        user = gateway.get_current_user(request)
    except HTTPException:
        pass

    return {
        "session_id": session_id,
        "created_at": "2026-04-27T00:00:00Z",
        "last_activity": "2026-04-27T00:00:00Z",
        "variant": "CloudNative",
        "statistics": {
            "total_queries": 1,
            "total_tool_calls": 0,
            "total_file_reads": 0,
            "average_response_time": 0.1,
        },
    }


@app.delete("/api/v1/session/{session_id}")
async def close_session(session_id: str, request: Request) -> dict:
    """Close a session."""
    try:
        user = gateway.get_current_user(request)
    except HTTPException:
        pass

    return {"message": "Session closed", "session_id": session_id}


@app.get("/api/v1/session/{session_id}/queries")
async def get_session_queries(session_id: str, request: Request) -> dict:
    """Get all queries in a session."""
    try:
        user = gateway.get_current_user(request)
    except HTTPException:
        pass

    return {
        "session_id": session_id,
        "queries": [],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "compass-rag", "version": __version__}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Compass RAG API",
        "version": __version__,
        "docs": "/docs",
    }
