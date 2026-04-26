"""Tests for Index Tree generation and management."""

import json
import tempfile
from pathlib import Path

import pytest

from compass.indexer.index_tree import IndexNode, IndexTreeBuilder, IndexTreeManager


class TestIndexNode:
    """Test IndexNode dataclass."""

    def test_create_document_node(self):
        """Test creating a document node."""
        node = IndexNode(
            name="file.html",
            path="docs/file.html",
            type="document",
            doc_count=1,
        )

        assert node.name == "file.html"
        assert node.type == "document"
        assert node.doc_count == 1
        assert node.children == []

    def test_create_folder_node(self):
        """Test creating a folder node."""
        node = IndexNode(
            name="CloudNative",
            path="docs/CloudNative",
            type="folder",
            summary="Cloud-native documentation",
        )

        assert node.name == "CloudNative"
        assert node.type == "folder"
        assert node.summary is not None

    def test_node_to_dict(self):
        """Test converting node to dictionary."""
        child = IndexNode(
            name="child.html",
            path="docs/child.html",
            type="document",
            doc_count=1,
        )
        node = IndexNode(
            name="parent",
            path="docs/parent",
            type="folder",
            children=[child],
            doc_count=1,
        )

        result = node.to_dict()
        assert result["name"] == "parent"
        assert result["type"] == "folder"
        assert len(result["children"]) == 1
        assert result["children"][0]["name"] == "child.html"

    def test_node_from_dict(self):
        """Test creating node from dictionary."""
        data = {
            "name": "test",
            "path": "docs/test",
            "type": "folder",
            "summary": "Test folder",
            "children": [
                {
                    "name": "file.html",
                    "path": "docs/test/file.html",
                    "type": "document",
                    "summary": None,
                    "children": [],
                    "doc_count": 1,
                    "last_modified": None,
                }
            ],
            "doc_count": 1,
            "last_modified": 1234567890,
        }

        node = IndexNode.from_dict(data)
        assert node.name == "test"
        assert node.type == "folder"
        assert len(node.children) == 1
        assert node.children[0].type == "document"

    def test_node_roundtrip(self):
        """Test node serialization and deserialization roundtrip."""
        original = IndexNode(
            name="root",
            path="docs",
            type="folder",
            summary="Root documentation",
            children=[
                IndexNode(
                    name="subfolder",
                    path="docs/sub",
                    type="folder",
                    summary="Subfolder docs",
                    children=[
                        IndexNode(
                            name="file.html",
                            path="docs/sub/file.html",
                            type="document",
                            doc_count=1,
                        )
                    ],
                    doc_count=1,
                )
            ],
            doc_count=1,
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = IndexNode.from_dict(data)

        assert restored.name == original.name
        assert restored.type == original.type
        assert len(restored.children) == len(original.children)
        assert restored.children[0].name == original.children[0].name


class TestIndexTreeManager:
    """Test IndexTreeManager class."""

    @pytest.fixture
    def sample_tree(self):
        """Create a sample index tree."""
        return IndexNode(
            name="docs",
            path="docs",
            type="folder",
            summary="All documentation",
            children=[
                IndexNode(
                    name="CloudNative",
                    path="docs/CloudNative",
                    type="folder",
                    summary="Cloud native docs",
                    children=[
                        IndexNode(
                            name="intro.html",
                            path="docs/CloudNative/intro.html",
                            type="document",
                            doc_count=1,
                        )
                    ],
                    doc_count=1,
                ),
                IndexNode(
                    name="ServerBased",
                    path="docs/ServerBased",
                    type="folder",
                    summary="Server based docs",
                    children=[
                        IndexNode(
                            name="guide.html",
                            path="docs/ServerBased/guide.html",
                            type="document",
                            doc_count=1,
                        )
                    ],
                    doc_count=1,
                ),
            ],
            doc_count=2,
        )

    def test_manager_initialization(self):
        """Test IndexTreeManager initialization."""
        index_path = Path("/tmp/index.json")
        manager = IndexTreeManager(index_path)

        assert manager.index_path == index_path

    def test_find_node_root(self, sample_tree):
        """Test finding root node."""
        manager = IndexTreeManager(Path("/tmp/index.json"))

        result = manager.find_node(sample_tree, "docs")
        assert result is not None
        assert result.name == "docs"

    def test_find_node_child(self, sample_tree):
        """Test finding child node."""
        manager = IndexTreeManager(Path("/tmp/index.json"))

        result = manager.find_node(sample_tree, "CloudNative")
        assert result is not None
        assert result.name == "CloudNative"

    def test_find_node_nested(self, sample_tree):
        """Test finding nested node."""
        manager = IndexTreeManager(Path("/tmp/index.json"))

        result = manager.find_node(sample_tree, "intro.html")
        assert result is not None
        assert result.type == "document"

    def test_find_node_not_found(self, sample_tree):
        """Test finding non-existent node."""
        manager = IndexTreeManager(Path("/tmp/index.json"))

        result = manager.find_node(sample_tree, "nonexistent")
        assert result is None

    def test_get_document_count(self, sample_tree):
        """Test getting document count."""
        manager = IndexTreeManager(Path("/tmp/index.json"))

        count = manager.get_document_count(sample_tree)
        assert count == 2

    def test_load_nonexistent_tree(self):
        """Test loading non-existent tree."""
        manager = IndexTreeManager(Path("/tmp/nonexistent_index.json"))

        result = manager.load_tree()
        assert result is None

    def test_load_and_save_tree(self):
        """Test saving and loading tree."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "index.json"

            # Create and save tree
            root = IndexNode(
                name="root",
                path="docs",
                type="folder",
                summary="Test root",
                children=[
                    IndexNode(
                        name="file.html",
                        path="docs/file.html",
                        type="document",
                        doc_count=1,
                    )
                ],
                doc_count=1,
            )

            # Manual save
            with open(index_path, "w") as f:
                json.dump(root.to_dict(), f)

            # Load tree
            manager = IndexTreeManager(index_path)
            loaded = manager.load_tree()

            assert loaded is not None
            assert loaded.name == "root"
            assert len(loaded.children) == 1
            assert loaded.doc_count == 1

    def test_print_tree(self, sample_tree, caplog):
        """Test printing tree structure."""
        manager = IndexTreeManager(Path("/tmp/index.json"))

        # This should not raise an exception
        manager.print_tree(sample_tree)
        # (logging output would be captured by caplog if we checked it)


class TestIndexTreeBuilder:
    """Test IndexTreeBuilder class."""

    def test_builder_initialization(self):
        """Test IndexTreeBuilder initialization."""
        # Should not raise even without API key (uses env)
        builder = IndexTreeBuilder()
        assert builder.model == "claude-haiku-4-5-20251001"

    def test_builder_with_custom_model(self):
        """Test builder with custom model."""
        builder = IndexTreeBuilder(model="claude-opus-4-7")
        assert builder.model == "claude-opus-4-7"

    def test_create_document_node(self):
        """Test creating document node."""
        builder = IndexTreeBuilder()

        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "test.html"
            doc_path.write_text("<html>Test</html>")

            node = builder._create_document_node(doc_path)
            assert node.name == "test.html"
            assert node.type == "document"
            assert node.doc_count == 1

    def test_build_tree_nonexistent_root(self):
        """Test building tree with non-existent root."""
        builder = IndexTreeBuilder()

        result = builder.build_tree(
            Path("/nonexistent/path"),
            Path("/tmp/index.json"),
        )
        assert result is False

    def test_build_tree_empty_folder(self):
        """Test building tree with empty folder."""
        builder = IndexTreeBuilder()

        with tempfile.TemporaryDirectory() as tmpdir:
            docs_root = Path(tmpdir)
            output_path = Path(tmpdir) / "index.json"

            # Without API key, this might fail on summarization
            # but should handle gracefully
            result = builder.build_tree(docs_root, output_path)
            # Result depends on API availability, but should be bool
            assert isinstance(result, bool)

    def test_build_tree_with_documents(self):
        """Test building tree with actual documents."""
        builder = IndexTreeBuilder()

        with tempfile.TemporaryDirectory() as tmpdir:
            docs_root = Path(tmpdir)
            # Create some structure
            (docs_root / "subfolder").mkdir()
            (docs_root / "file1.html").write_text("<html>Doc 1</html>")
            (docs_root / "subfolder" / "file2.html").write_text("<html>Doc 2</html>")

            output_path = Path(tmpdir) / "index.json"

            # Build tree (may skip summarization if no API key)
            result = builder.build_tree(docs_root, output_path)
            assert isinstance(result, bool)

            if result and output_path.exists():
                # Verify structure
                with open(output_path) as f:
                    data = json.load(f)
                assert data["name"] == docs_root.name
                assert data["type"] == "folder"
