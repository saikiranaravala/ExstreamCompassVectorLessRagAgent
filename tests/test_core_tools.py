"""Tests for core agent tools."""

import tempfile
from pathlib import Path

import pytest

from compass.agent.core_tools import (
    ListNodeTool,
    ReadHTMLTool,
    ReadPDFTool,
    LexicalSearchTool,
    CompareVariantsTool,
    ToolRegistry,
    ToolResult,
)


class TestToolResult:
    """Test ToolResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful result."""
        result = ToolResult(success=True, data={"key": "value"})

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_failed_result(self):
        """Test creating a failed result."""
        result = ToolResult(
            success=False,
            data=None,
            error="Tool execution failed",
        )

        assert result.success is False
        assert result.data is None
        assert result.error == "Tool execution failed"


class TestListNodeTool:
    """Test ListNodeTool."""

    def test_list_node_without_index(self):
        """Test list_node when index is not initialized."""
        tool = ListNodeTool(index_tree=None)

        result = tool.execute(
            node_path="docs/CloudNative",
            variant="CloudNative",
        )

        assert result.success is False
        assert result.error is not None

    def test_list_node_with_index(self):
        """Test list_node with initialized index."""
        tool = ListNodeTool(index_tree={})  # Mock index

        result = tool.execute(
            node_path="docs/CloudNative",
            variant="CloudNative",
        )

        assert result.success is True
        assert "children" in result.data
        assert isinstance(result.data["children"], list)


class TestReadHTMLTool:
    """Test ReadHTMLTool."""

    def test_read_html_file_not_found(self):
        """Test reading non-existent HTML file."""
        tool = ReadHTMLTool()

        result = tool.execute(
            file_path="/nonexistent/file.html",
            variant="CloudNative",
        )

        assert result.success is False
        assert result.error is not None

    def test_read_html_valid_file(self):
        """Test reading a valid HTML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            html_file = Path(tmpdir) / "test.html"
            html_file.write_text("<html><body>Test content</body></html>")

            tool = ReadHTMLTool(docs_root=tmpdir)

            result = tool.execute(
                file_path=str(html_file),
                variant="CloudNative",
            )

            assert result.success is True
            assert "title" in result.data
            assert "content" in result.data
            assert "url" in result.data

    def test_read_html_non_html_file(self):
        """Test reading non-HTML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "test.txt"
            txt_file.write_text("Not HTML")

            tool = ReadHTMLTool()

            result = tool.execute(
                file_path=str(txt_file),
                variant="CloudNative",
            )

            assert result.success is False


class TestReadPDFTool:
    """Test ReadPDFTool."""

    def test_read_pdf_file_not_found(self):
        """Test reading non-existent PDF file."""
        tool = ReadPDFTool()

        result = tool.execute(
            file_path="/nonexistent/file.pdf",
            variant="CloudNative",
        )

        assert result.success is False
        assert result.error is not None

    def test_read_pdf_with_page_number(self):
        """Test reading PDF with specific page."""
        tool = ReadPDFTool()

        result = tool.execute(
            file_path="/path/to/file.pdf",
            variant="CloudNative",
            page=1,
        )

        # Will fail since file doesn't exist, but shows parameter support
        assert result.success is False


class TestLexicalSearchTool:
    """Test LexicalSearchTool."""

    def test_search_without_index(self):
        """Test search when index is not initialized."""
        tool = LexicalSearchTool(search_index=None)

        result = tool.execute(
            query="Python programming",
            variant="CloudNative",
            limit=10,
        )

        assert result.success is False
        assert result.error is not None

    def test_search_with_results(self):
        """Test search execution."""
        # Mock search index that returns results
        class MockIndex:
            def search(self, query, limit):
                from compass.indexer.search import SearchResult

                return [
                    SearchResult(
                        doc_id="doc1",
                        title="Python Guide",
                        path="docs/python.html",
                        score=0.95,
                        content_preview="Python is a language",
                    )
                ]

        tool = LexicalSearchTool(search_index=MockIndex())

        result = tool.execute(
            query="Python",
            variant="CloudNative",
            limit=10,
        )

        assert result.success is True
        assert "results" in result.data
        assert "total" in result.data
        assert result.data["total"] == 1

    def test_search_with_custom_limit(self):
        """Test search with custom result limit."""
        class MockIndex:
            def search(self, query, limit):
                return []

        tool = LexicalSearchTool(search_index=MockIndex())

        result = tool.execute(
            query="test",
            variant="ServerBased",
            limit=5,
        )

        assert result.success is True


class TestCompareVariantsTool:
    """Test CompareVariantsTool."""

    def test_compare_variants(self):
        """Test variant comparison."""
        tool = CompareVariantsTool(index_tree={})

        result = tool.execute(
            topic="deployment",
            query="How to deploy?",
        )

        assert result.success is True
        assert "topic" in result.data
        assert "cloudnative" in result.data
        assert "serverbased" in result.data

    def test_compare_variants_without_query(self):
        """Test comparison without query."""
        tool = CompareVariantsTool(index_tree={})

        result = tool.execute(topic="authentication")

        assert result.success is True
        assert result.data["topic"] == "authentication"


class TestToolRegistry:
    """Test ToolRegistry."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = ToolRegistry()

        assert registry.tools is not None
        assert len(registry.tools) == 5

    def test_registry_get_tools(self):
        """Test getting tools from registry."""
        registry = ToolRegistry()

        tools = registry.get_tools()

        assert "list_node" in tools
        assert "read_html" in tools
        assert "read_pdf" in tools
        assert "lexical_search" in tools
        assert "compare_variants" in tools

    def test_registry_list_tools(self):
        """Test listing tool descriptions."""
        registry = ToolRegistry()

        tool_list = registry.list_tools()

        assert len(tool_list) == 5
        assert all("name" in tool for tool in tool_list)
        assert all("description" in tool for tool in tool_list)
        assert all("params" in tool for tool in tool_list)

    def test_registry_execute_valid_tool(self):
        """Test executing a valid tool."""
        registry = ToolRegistry()

        result = registry.execute_tool(
            "compare_variants",
            topic="testing",
        )

        assert result.success is True

    def test_registry_execute_invalid_tool(self):
        """Test executing an invalid tool."""
        registry = ToolRegistry()

        result = registry.execute_tool(
            "nonexistent_tool",
            some_arg="value",
        )

        assert result.success is False
        assert "Unknown tool" in result.error

    def test_registry_execute_with_invalid_args(self):
        """Test executing tool with invalid arguments."""
        registry = ToolRegistry()

        result = registry.execute_tool(
            "list_node",
            # Missing required arguments
        )

        assert result.success is False

    def test_registry_with_custom_components(self):
        """Test registry with custom components."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ToolRegistry(docs_root=tmpdir)

            tools = registry.get_tools()
            assert "read_html" in tools

    def test_tool_result_format(self):
        """Test that tool results have consistent format."""
        registry = ToolRegistry()

        result = registry.execute_tool(
            "compare_variants",
            topic="test",
        )

        assert hasattr(result, "success")
        assert hasattr(result, "data")
        assert hasattr(result, "error")
        assert isinstance(result.success, bool)
