"""Core tools for the reasoning agent.

Tools are thin wrappers over the shared retrieval layer (``QueryService``),
so the agent path and the API path search the same index and read the same
corpus. Every tool degrades to an explanatory error ToolResult when its
dependencies were not injected.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    from langsmith import traceable as _traceable
except ImportError:
    def _traceable(func=None, **kwargs):  # no-op decorator when langsmith not installed
        if func is not None:
            return func
        return lambda f: f

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: Any
    error: Optional[str] = None


class ListNodeTool:
    """List the contents of a documentation tree node (folder)."""

    def __init__(self, index_tree: Optional[Any] = None, docs_root: Optional[Path] = None):
        self.index_tree = index_tree
        self.docs_root = Path(docs_root) if docs_root else None

    def execute(self, node_path: str, variant: str) -> ToolResult:
        """List children of a node.

        Args:
            node_path: Folder path relative to the docs root ("" for the variant root)
            variant: Variant filter (CloudNative or ServerBased)
        """
        try:
            if self.docs_root and self.docs_root.exists():
                base = (self.docs_root / variant).resolve()
                target = (self.docs_root / node_path).resolve() if node_path else base
                try:
                    target.relative_to(base)
                except ValueError:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"Path outside {variant} subtree (variant isolation)",
                    )
                if not target.is_dir():
                    return ToolResult(success=False, data=None, error=f"Not a folder: {node_path}")
                children = [
                    {
                        "name": p.name,
                        "type": "folder" if p.is_dir() else "document",
                    }
                    for p in sorted(target.iterdir())[:100]
                    if p.is_dir() or p.suffix.lower() in (".htm", ".html", ".pdf")
                ]
                return ToolResult(success=True, data={"node": node_path, "children": children})

            if self.index_tree is not None:
                node = self.index_tree
                for part in filter(None, node_path.replace("\\", "/").split("/")):
                    node = node.get(part, {}) if isinstance(node, dict) else {}
                children = (
                    [{"name": k, "type": "folder" if isinstance(v, dict) else "document"}
                     for k, v in node.items()]
                    if isinstance(node, dict)
                    else []
                )
                return ToolResult(success=True, data={"node": node_path, "children": children})

            return ToolResult(success=False, data=None, error="Index tree not initialized")
        except Exception as e:
            logger.error(f"list_node failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class ReadHTMLTool:
    """Read and parse an HTML documentation file (.htm or .html)."""

    MAX_CONTENT_CHARS = 4000

    def __init__(self, docs_root: Optional[Path] = None):
        self.docs_root = Path(docs_root) if docs_root else None

    def execute(self, file_path: str, variant: str) -> ToolResult:
        try:
            from compass.retrieval.textutil import extract_html_text

            path = Path(file_path)
            if self.docs_root and not path.is_absolute():
                path = self.docs_root / file_path
            path = path.resolve()

            if path.suffix.lower() not in (".htm", ".html"):
                return ToolResult(success=False, data=None, error=f"Not an HTML file: {file_path}")
            if not path.is_file():
                return ToolResult(success=False, data=None, error=f"File not found: {file_path}")

            if self.docs_root:
                root = self.docs_root.resolve()
                try:
                    path.relative_to(root)
                except ValueError:
                    return ToolResult(
                        success=False, data=None, error="Path outside documentation root"
                    )
                variant_root = root / variant
                if variant_root.is_dir():
                    try:
                        path.relative_to(variant_root)
                    except ValueError:
                        return ToolResult(
                            success=False,
                            data=None,
                            error=f"Path outside {variant} subtree (variant isolation)",
                        )

            html = path.read_text(encoding="utf-8", errors="ignore")
            title, text = extract_html_text(html)
            return ToolResult(
                success=True,
                data={
                    "title": title or path.stem,
                    "content": text[: self.MAX_CONTENT_CHARS],
                    "url": str(path),
                },
            )
        except Exception as e:
            logger.error(f"read_html failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class ReadPDFTool:
    """Read and extract text from a PDF documentation file."""

    def __init__(self, docs_root: Optional[Path] = None):
        self.docs_root = Path(docs_root) if docs_root else None

    def execute(self, file_path: str, variant: str, page: Optional[int] = None) -> ToolResult:
        try:
            path = Path(file_path)
            if self.docs_root and not path.is_absolute():
                path = self.docs_root / file_path
            path = path.resolve()

            if path.suffix.lower() != ".pdf" or not path.is_file():
                return ToolResult(
                    success=False, data=None, error=f"Could not read PDF file: {file_path}"
                )

            from compass.indexer.pdf_parser import PDFParser

            parsed = PDFParser.parse_file(path)
            if not parsed:
                return ToolResult(
                    success=False, data=None, error=f"Could not parse PDF: {file_path}"
                )
            content = parsed.text[:4000] if page is None else parsed.text
            return ToolResult(
                success=True,
                data={
                    "title": parsed.title,
                    "content": content,
                    "pages": parsed.pages,
                    "url": parsed.url,
                },
            )
        except Exception as e:
            logger.error(f"read_pdf failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class LexicalSearchTool:
    """Full-text BM25 search over the documentation corpus."""

    def __init__(self, search_index: Optional[Any] = None, service: Optional[Any] = None):
        """Args:
            search_index: Legacy index object exposing .search(query, limit)
            service: QueryService (preferred) — searches per variant with passages
        """
        self.search_index = search_index
        self.service = service

    def execute(self, query: str, variant: str, limit: int = 10) -> ToolResult:
        try:
            if self.service is not None:
                hits = self.service.search(query, variant, limit=limit)
                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "results": [
                            {
                                "doc_id": h["doc_id"],
                                "title": h["title"],
                                "path": h["path"],
                                "score": h["score"],
                                "preview": h["passage"][:300],
                            }
                            for h in hits
                        ],
                        "total": len(hits),
                    },
                )

            if self.search_index is not None:
                results = self.search_index.search(query, limit=limit)
                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "results": [
                            {
                                "doc_id": r.doc_id,
                                "title": r.title,
                                "path": r.path,
                                "score": r.score,
                                "preview": r.content_preview[:200],
                            }
                            for r in results
                        ],
                        "total": len(results),
                    },
                )

            return ToolResult(success=False, data=None, error="Search index not initialized")
        except Exception as e:
            logger.error(f"lexical_search failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class CompareVariantsTool:
    """Compare a topic across CloudNative and ServerBased documentation."""

    def __init__(self, index_tree: Optional[Any] = None, service: Optional[Any] = None):
        self.index_tree = index_tree
        self.service = service

    def execute(self, topic: str, query: Optional[str] = None) -> ToolResult:
        try:
            search_text = query or topic
            comparison: dict[str, Any] = {"topic": topic}

            for variant, key in (("CloudNative", "cloudnative"), ("ServerBased", "serverbased")):
                if self.service is not None:
                    hits = self.service.search(search_text, variant, limit=3)
                    comparison[key] = {
                        "availability": bool(hits),
                        "docs": [h["path"] for h in hits],
                        "summary": hits[0]["passage"][:300] if hits else "No matching topics found",
                    }
                else:
                    comparison[key] = {
                        "availability": None,
                        "docs": [],
                        "summary": "Search service not initialized",
                    }

            return ToolResult(success=True, data=comparison)
        except Exception as e:
            logger.error(f"compare_variants failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class ToolRegistry:
    """Registry of available tools for the agent."""

    def __init__(self, index_tree=None, search_index=None, docs_root=None, service=None):
        """Initialize tool registry.

        Args:
            index_tree: Index tree (dict) for offline node listing
            search_index: Legacy BM25 index object
            docs_root: Root documentation directory
            service: QueryService — the preferred backend for search/compare
        """
        self.tools = {
            "list_node": ListNodeTool(index_tree, docs_root),
            "read_html": ReadHTMLTool(docs_root),
            "read_pdf": ReadPDFTool(docs_root),
            "lexical_search": LexicalSearchTool(search_index, service),
            "compare_variants": CompareVariantsTool(index_tree, service),
        }

    @_traceable(name="tool_execution", run_type="tool")
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a registered tool by name."""
        if tool_name not in self.tools:
            return ToolResult(success=False, data=None, error=f"Unknown tool: {tool_name}")

        try:
            return self.tools[tool_name].execute(**kwargs)
        except TypeError as e:
            return ToolResult(
                success=False, data=None, error=f"Invalid arguments for {tool_name}: {e}"
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def get_tools(self) -> dict:
        """Get all registered tools."""
        return self.tools

    def list_tools(self) -> list[dict]:
        """Get list of available tools with descriptions."""
        return [
            {
                "name": "list_node",
                "description": "List contents of a documentation folder",
                "params": ["node_path", "variant"],
            },
            {
                "name": "read_html",
                "description": "Read and parse HTML documentation files (.htm/.html)",
                "params": ["file_path", "variant"],
            },
            {
                "name": "read_pdf",
                "description": "Read and extract PDF documentation",
                "params": ["file_path", "variant", "page"],
            },
            {
                "name": "lexical_search",
                "description": "Full-text BM25 search across documentation",
                "params": ["query", "variant", "limit"],
            },
            {
                "name": "compare_variants",
                "description": "Compare CloudNative vs ServerBased documentation",
                "params": ["topic", "query"],
            },
        ]
