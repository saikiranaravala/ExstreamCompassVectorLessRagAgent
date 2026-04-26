"""Tests for variant isolation and enforcement."""

import pytest

from compass.agent.variant_isolation import (
    VariantConfig,
    VariantIsolationManager,
    VariantEnforcer,
)


class TestVariantConfig:
    """Test VariantConfig dataclass."""

    def test_create_variant_config(self):
        """Test creating variant configuration."""
        config = VariantConfig(
            name="TestVariant",
            root_path="docs/test",
            allowed_prefixes=["docs/test/", "test/"],
            description="Test documentation",
        )

        assert config.name == "TestVariant"
        assert config.root_path == "docs/test"
        assert len(config.allowed_prefixes) == 2


class TestVariantIsolationManager:
    """Test VariantIsolationManager class."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = VariantIsolationManager()

        assert manager.docs_root.name == "docs"
        assert len(manager.variants) == 3

    def test_validate_variant_cloudnative(self):
        """Test validating CloudNative variant."""
        manager = VariantIsolationManager()

        assert manager.validate_variant("CloudNative") is True

    def test_validate_variant_serverbased(self):
        """Test validating ServerBased variant."""
        manager = VariantIsolationManager()

        assert manager.validate_variant("ServerBased") is True

    def test_validate_invalid_variant(self):
        """Test validating invalid variant."""
        manager = VariantIsolationManager()

        assert manager.validate_variant("InvalidVariant") is False

    def test_get_variant(self):
        """Test getting variant configuration."""
        manager = VariantIsolationManager()

        variant = manager.get_variant("CloudNative")
        assert variant is not None
        assert variant.name == "CloudNative"

    def test_get_invalid_variant(self):
        """Test getting invalid variant."""
        manager = VariantIsolationManager()

        variant = manager.get_variant("InvalidVariant")
        assert variant is None

    def test_is_path_in_cloudnative_variant(self):
        """Test checking path in CloudNative variant."""
        manager = VariantIsolationManager()

        assert manager.is_path_in_variant("docs/CloudNative/intro.html", "CloudNative") is True
        assert manager.is_path_in_variant(
            "CloudNative/guides/intro.html",
            "CloudNative",
        ) is True

    def test_is_path_not_in_cloudnative_variant(self):
        """Test checking path not in CloudNative variant."""
        manager = VariantIsolationManager()

        assert (
            manager.is_path_in_variant("docs/ServerBased/intro.html", "CloudNative")
            is False
        )

    def test_is_path_in_serverbased_variant(self):
        """Test checking path in ServerBased variant."""
        manager = VariantIsolationManager()

        assert (
            manager.is_path_in_variant("docs/ServerBased/intro.html", "ServerBased")
            is True
        )
        assert (
            manager.is_path_in_variant(
                "CommunicationsDesigner/intro.html",
                "ServerBased",
            )
            is True
        )

    def test_enforce_variant_path_allowed(self):
        """Test enforcing allowed path."""
        manager = VariantIsolationManager()

        result = manager.enforce_variant_path(
            "docs/CloudNative/intro.html",
            "CloudNative",
        )

        assert result == "docs/CloudNative/intro.html"

    def test_enforce_variant_path_denied(self):
        """Test enforcing denied path."""
        manager = VariantIsolationManager()

        result = manager.enforce_variant_path(
            "docs/ServerBased/intro.html",
            "CloudNative",
        )

        assert result is None

    def test_filter_search_results(self):
        """Test filtering search results."""
        manager = VariantIsolationManager()

        results = [
            {"path": "docs/CloudNative/file1.html", "title": "CN Doc 1"},
            {"path": "docs/ServerBased/file2.html", "title": "SB Doc 1"},
            {"path": "docs/CloudNative/file3.html", "title": "CN Doc 2"},
        ]

        filtered = manager.filter_search_results(results, "CloudNative")

        assert len(filtered) == 2
        assert all("CloudNative" in r["path"] for r in filtered)

    def test_filter_search_results_empty(self):
        """Test filtering empty search results."""
        manager = VariantIsolationManager()

        filtered = manager.filter_search_results([], "CloudNative")

        assert filtered == []

    def test_get_variant_root(self):
        """Test getting variant root path."""
        manager = VariantIsolationManager()

        root = manager.get_variant_root("CloudNative")

        assert root is not None
        assert "CloudNative" in str(root)

    def test_get_invalid_variant_root(self):
        """Test getting root for invalid variant."""
        manager = VariantIsolationManager()

        root = manager.get_variant_root("InvalidVariant")

        assert root is None

    def test_list_variants(self):
        """Test listing available variants."""
        manager = VariantIsolationManager()

        variants = manager.list_variants()

        assert len(variants) == 3
        assert any(v["name"] == "CloudNative" for v in variants)
        assert any(v["name"] == "ServerBased" for v in variants)


class TestVariantEnforcer:
    """Test VariantEnforcer class."""

    @pytest.fixture
    def enforcer(self):
        """Create enforcer with manager."""
        manager = VariantIsolationManager()
        return VariantEnforcer(manager)

    def test_can_read_document_allowed(self, enforcer):
        """Test reading allowed document."""
        assert (
            enforcer.can_read_document(
                "docs/CloudNative/file.html",
                "CloudNative",
            )
            is True
        )

    def test_can_read_document_denied(self, enforcer):
        """Test reading denied document."""
        assert (
            enforcer.can_read_document(
                "docs/ServerBased/file.html",
                "CloudNative",
            )
            is False
        )

    def test_can_search_variant(self, enforcer):
        """Test searching in variant."""
        assert enforcer.can_search_variant("Python", "CloudNative") is True
        assert enforcer.can_search_variant("Java", "ServerBased") is True

    def test_can_search_invalid_variant(self, enforcer):
        """Test searching in invalid variant."""
        assert enforcer.can_search_variant("test", "InvalidVariant") is False

    def test_enforce_read_html_tool(self, enforcer):
        """Test enforcing read_html tool."""
        tool_args = {"file_path": "docs/CloudNative/file.html"}

        assert enforcer.enforce_tool_call("read_html", tool_args, "CloudNative") is True

    def test_enforce_read_html_tool_denied(self, enforcer):
        """Test enforcing read_html tool with denied path."""
        tool_args = {"file_path": "docs/ServerBased/file.html"}

        assert enforcer.enforce_tool_call("read_html", tool_args, "CloudNative") is False

    def test_enforce_lexical_search_tool(self, enforcer):
        """Test enforcing lexical_search tool."""
        tool_args = {"query": "Python"}

        assert (
            enforcer.enforce_tool_call("lexical_search", tool_args, "CloudNative") is True
        )

    def test_enforce_compare_variants_tool(self, enforcer):
        """Test that compare_variants is always allowed."""
        tool_args = {"topic": "deployment"}

        assert (
            enforcer.enforce_tool_call("compare_variants", tool_args, "CloudNative")
            is True
        )

    def test_filter_search_results(self, enforcer):
        """Test filtering search results output."""
        output = {
            "results": [
                {"path": "docs/CloudNative/file1.html"},
                {"path": "docs/ServerBased/file2.html"},
            ]
        }

        filtered = enforcer.filter_tool_output("lexical_search", output, "CloudNative")

        assert len(filtered["results"]) == 1
        assert "CloudNative" in filtered["results"][0]["path"]

    def test_filter_list_node_output(self, enforcer):
        """Test filtering list_node output."""
        output = {
            "children": [
                {"name": "file1.html", "path": "docs/CloudNative/file1.html"},
                {"name": "file2.html", "path": "docs/ServerBased/file2.html"},
            ]
        }

        filtered = enforcer.filter_tool_output("list_node", output, "CloudNative")

        assert len(filtered["children"]) == 1

    def test_validate_cloudnative_answer(self, enforcer):
        """Test validating CloudNative answer."""
        answer = "In CloudNative, use Kubernetes for deployment"

        assert enforcer.validate_answer(answer, "CloudNative") is True

    def test_validate_answer_with_forbidden_term(self, enforcer):
        """Test validating answer with forbidden term."""
        answer = "In CloudNative, use on-premise servers"

        # Should detect forbidden term
        result = enforcer.validate_answer(answer, "CloudNative")
        # Note: function returns False on forbidden terms
        assert result is False

    def test_validate_serverbased_answer(self, enforcer):
        """Test validating ServerBased answer."""
        answer = "In ServerBased, configure the server deployment"

        assert enforcer.validate_answer(answer, "ServerBased") is True
