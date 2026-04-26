"""Core tools for the reasoning agent."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: Any
    error: Optional[str] = None


class ListNodeTool:
    """Tool to list contents of index tree nodes."""

    def __init__(self, index_tree: Optional[Any] = None):
        """Initialize tool.

        Args:
            index_tree: Index tree manager instance
        """
        self.index_tree = index_tree

    def execute(self, node_path: str, variant: str) -> ToolResult:
        """List children of an index tree node.

        Args:
            node_path: Path to node in index tree
            variant: Variant filter (CloudNative or ServerBased)

        Returns:
            ToolResult with list of child nodes
        """
        try:
            if not self.index_tree:
                return ToolResult(
                    success=False,
                    data=None,
                    error="Index tree not initialized",
                )

            # In production, would traverse the actual index tree
            logger.info(f"Listing node: {node_path} (variant: {variant})")

            children = [
                {"name": "intro.html", "type": "document"},
                {"name": "guide.html", "type": "document"},
                {"name": "advanced", "type": "folder"},
            ]

            return ToolResult(
                success=True,
                data={"node": node_path, "children": children},
            )

        except Exception as e:
            logger.error(f"list_node failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class ReadHTMLTool:
    """Tool to read HTML documentation files."""

    def __init__(self, docs_root: Optional[Path] = None):
        """Initialize tool.

        Args:
            docs_root: Root documentation directory
        """
        self.docs_root = Path(docs_root) if docs_root else None

    def execute(self, file_path: str, variant: str) -> ToolResult:
        """Read and parse HTML file.

        Args:
            file_path: Path to HTML file
            variant: Documentation variant (for validation)

        Returns:
            ToolResult with parsed HTML content
        """
        try:
            logger.info(f"Reading HTML: {file_path} (variant: {variant})")

            # In production, would use the HTML parser
            from compass.indexer.html_parser import HTMLParser

            full_path = Path(file_path)

            if full_path.exists() and full_path.suffix == ".html":
                parsed = HTMLParser.parse_file(full_path)
                if parsed:
                    return ToolResult(
                        success=True,
                        data={
                            "title": parsed.title,
                            "content": parsed.text[:1000],  # Truncate for response
                            "url": parsed.url,
                        },
                    )

            return ToolResult(
                success=False,
                data=None,
                error=f"Could not read HTML file: {file_path}",
            )

        except Exception as e:
            logger.error(f"read_html failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class ReadPDFTool:
    """Tool to read PDF documentation files."""

    def __init__(self, docs_root: Optional[Path] = None):
        """Initialize tool.

        Args:
            docs_root: Root documentation directory
        """
        self.docs_root = Path(docs_root) if docs_root else None

    def execute(self, file_path: str, variant: str, page: Optional[int] = None) -> ToolResult:
        """Read and extract PDF content.

        Args:
            file_path: Path to PDF file
            variant: Documentation variant (for validation)
            page: Optional specific page number

        Returns:
            ToolResult with extracted PDF content
        """
        try:
            logger.info(f"Reading PDF: {file_path} (variant: {variant}, page: {page})")

            # In production, would use the PDF parser
            from compass.indexer.pdf_parser import PDFParser

            full_path = Path(file_path)

            if full_path.exists() and full_path.suffix == ".pdf":
                parsed = PDFParser.parse_file(full_path)
                if parsed:
                    content = parsed.text[:1000] if page is None else parsed.text
                    return ToolResult(
                        success=True,
                        data={
                            "title": parsed.title,
                            "content": content,
                            "pages": parsed.pages,
                            "url": parsed.url,
                        },
                    )

            return ToolResult(
                success=False,
                data=None,
                error=f"Could not read PDF file: {file_path}",
            )

        except Exception as e:
            logger.error(f"read_pdf failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class LexicalSearchTool:
    """Tool for BM25 full-text search."""

    def __init__(self, search_index: Optional[Any] = None):
        """Initialize tool.

        Args:
            search_index: BM25Index instance
        """
        self.search_index = search_index

    def execute(
        self,
        query: str,
        variant: str,
        limit: int = 10,
    ) -> ToolResult:
        """Execute lexical search query.

        Args:
            query: Search query string
            variant: Documentation variant to search
            limit: Maximum results to return

        Returns:
            ToolResult with search results
        """
        try:
            logger.info(f"Searching: '{query}' in {variant} (limit: {limit})")

            if not self.search_index:
                return ToolResult(
                    success=False,
                    data=None,
                    error="Search index not initialized",
                )

            # In production, would use the actual search index
            from compass.indexer.search import BM25Index

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

        except Exception as e:
            logger.error(f"lexical_search failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class CompareVariantsTool:
    """Tool to compare CloudNative vs ServerBased documentation."""

    def __init__(self, index_tree: Optional[Any] = None):
        """Initialize tool.

        Args:
            index_tree: Index tree manager instance
        """
        self.index_tree = index_tree

    def execute(
        self,
        topic: str,
        query: Optional[str] = None,
    ) -> ToolResult:
        """Compare a topic across variants.

        Args:
            topic: Topic to compare
            query: Optional query string for filtering

        Returns:
            ToolResult with comparison data
        """
        try:
            logger.info(f"Comparing variants for topic: {topic}")

            comparison = {
                "topic": topic,
                "cloudnative": {
                    "availability": True,
                    "docs": ["cloud-intro.html", "cloud-guide.html"],
                    "summary": "Cloud-native specific documentation available",
                },
                "serverbased": {
                    "availability": True,
                    "docs": ["server-guide.html", "server-setup.html"],
                    "summary": "Server-based specific documentation available",
                },
            }

            return ToolResult(success=True, data=comparison)

        except Exception as e:
            logger.error(f"compare_variants failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class ToolRegistry:
    """Registry of available tools for the agent."""

    def __init__(self, index_tree=None, search_index=None, docs_root=None):
        """Initialize tool registry.

        Args:
            index_tree: Index tree manager
            search_index: BM25 search index
            docs_root: Root documentation directory
        """
        self.tools = {
            "list_node": ListNodeTool(index_tree),
            "read_html": ReadHTMLTool(docs_root),
            "read_pdf": ReadPDFTool(docs_root),
            "lexical_search": LexicalSearchTool(search_index),
            "compare_variants": CompareVariantsTool(index_tree),
        }

    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a registered tool.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool arguments

        Returns:
            ToolResult
        """
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                data=None,
                error=f"Unknown tool: {tool_name}",
            )

        try:
            tool = self.tools[tool_name]
            return tool.execute(**kwargs)
        except TypeError as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid arguments for {tool_name}: {e}",
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def get_tools(self) -> dict:
        """Get all registered tools.

        Returns:
            Dict of tool names and instances
        """
        return self.tools

    def list_tools(self) -> list[dict]:
        """Get list of available tools with descriptions.

        Returns:
            List of tool descriptions
        """
        return [
            {
                "name": "list_node",
                "description": "List contents of an index tree node",
                "params": ["node_path", "variant"],
            },
            {
                "name": "read_html",
                "description": "Read and parse HTML documentation files",
                "params": ["file_path", "variant"],
            },
            {
                "name": "read_pdf",
                "description": "Read and extract PDF documentation",
                "params": ["file_path", "variant", "page"],
            },
            {
                "name": "lexical_search",
                "description": "Full-text search across documentation",
                "params": ["query", "variant", "limit"],
            },
            {
                "name": "compare_variants",
                "description": "Compare CloudNative vs ServerBased documentation",
                "params": ["topic", "query"],
            },
        ]
