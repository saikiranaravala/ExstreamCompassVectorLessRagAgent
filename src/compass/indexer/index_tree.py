"""Index Tree generation and management with LLM summarization."""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from anthropic import Anthropic

from compass.indexer.atomic import AtomicWriter

logger = logging.getLogger(__name__)


@dataclass
class IndexNode:
    """Node in the Index Tree."""

    name: str
    path: str
    type: str  # "folder" or "document"
    summary: Optional[str] = None
    children: list["IndexNode"] = None
    doc_count: int = 0
    last_modified: Optional[int] = None

    def __post_init__(self):
        """Initialize children list if not provided."""
        if self.children is None:
            self.children = []

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "summary": self.summary,
            "children": [child.to_dict() for child in self.children],
            "doc_count": self.doc_count,
            "last_modified": self.last_modified,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IndexNode":
        """Create node from dictionary representation."""
        children = [cls.from_dict(child) for child in data.get("children", [])]
        return cls(
            name=data["name"],
            path=data["path"],
            type=data["type"],
            summary=data.get("summary"),
            children=children,
            doc_count=data.get("doc_count", 0),
            last_modified=data.get("last_modified"),
        )


class IndexTreeBuilder:
    """Build Index Tree with LLM summarization."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-haiku-4-5-20251001"):
        """Initialize builder.

        Args:
            api_key: Anthropic API key (uses env var if not provided)
            model: Claude model to use for summarization
        """
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model = model

    def build_tree(self, docs_root: Path, output_path: Path) -> bool:
        """Build complete index tree from documentation folder.

        Args:
            docs_root: Root documentation folder
            output_path: Path to save index tree JSON

        Returns:
            True if successful
        """
        docs_root = Path(docs_root)

        if not docs_root.exists():
            logger.error(f"Documentation root does not exist: {docs_root}")
            return False

        try:
            logger.info(f"Building index tree from {docs_root}")
            root_node = self._build_node_recursive(docs_root)

            # Save using atomic write
            def write_func(f):
                json.dump(root_node.to_dict(), f, indent=2)

            success = AtomicWriter.write_file(output_path, write_func)

            if success:
                logger.info(f"Index tree saved to {output_path}")
                return True
            else:
                logger.error("Failed to write index tree")
                return False

        except Exception as e:
            logger.error(f"Index tree building failed: {e}")
            return False

    def _build_node_recursive(self, path: Path) -> IndexNode:
        """Recursively build index node for path.

        Args:
            path: File or folder path

        Returns:
            IndexNode
        """
        if path.is_file():
            return self._create_document_node(path)

        # It's a folder
        node = IndexNode(
            name=path.name,
            path=str(path.relative_to(path.parent.parent)) if path.parent.parent.exists() else str(path),
            type="folder",
        )

        # Process children
        for child_path in sorted(path.iterdir()):
            if child_path.name.startswith("."):
                continue

            child_node = self._build_node_recursive(child_path)
            node.children.append(child_node)
            node.doc_count += child_node.doc_count if child_node.type == "document" else child_node.doc_count

        # Summarize folder if it has documents
        if node.doc_count > 0:
            node.summary = self._summarize_node(node)

        return node

    def _create_document_node(self, file_path: Path) -> IndexNode:
        """Create node for a document file.

        Args:
            file_path: Path to document

        Returns:
            IndexNode for document
        """
        return IndexNode(
            name=file_path.name,
            path=str(file_path),
            type="document",
            doc_count=1,
        )

    def _summarize_node(self, node: IndexNode) -> Optional[str]:
        """Generate summary for folder node using Claude.

        Args:
            node: IndexNode to summarize

        Returns:
            Summary string or None if failed
        """
        if not node.children:
            return None

        # Build content from child names and summaries
        child_names = [child.name for child in node.children if child.type == "document"]
        child_summaries = [
            child.summary for child in node.children if child.type == "folder" and child.summary
        ]

        if not child_names and not child_summaries:
            return None

        prompt = f"""Summarize the following documentation folder structure in 1-2 sentences.

Folder: {node.name}
Documents: {', '.join(child_names[:10])}
{'Subfolders: ' + ', '.join(str(s[:50]) for s in child_summaries[:3]) if child_summaries else ''}

Provide a concise summary of what this section covers."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )

            summary = message.content[0].text.strip()
            logger.debug(f"Summarized {node.name}: {summary[:80]}...")
            return summary

        except Exception as e:
            logger.warning(f"Failed to summarize {node.name}: {e}")
            return None


class IndexTreeManager:
    """Manage Index Tree operations."""

    def __init__(self, index_path: Path):
        """Initialize manager.

        Args:
            index_path: Path to index tree JSON file
        """
        self.index_path = Path(index_path)

    def load_tree(self) -> Optional[IndexNode]:
        """Load index tree from file.

        Returns:
            Root IndexNode or None if failed
        """
        try:
            if not self.index_path.exists():
                logger.warning(f"Index tree does not exist: {self.index_path}")
                return None

            with open(self.index_path, "r") as f:
                data = json.load(f)

            root = IndexNode.from_dict(data)
            logger.info(f"Loaded index tree with {root.doc_count} documents")
            return root

        except Exception as e:
            logger.error(f"Failed to load index tree: {e}")
            return None

    def find_node(self, root: IndexNode, name: str) -> Optional[IndexNode]:
        """Find node by name in tree.

        Args:
            root: Root node to search from
            name: Node name to find

        Returns:
            IndexNode or None if not found
        """
        if root.name == name:
            return root

        for child in root.children:
            result = self.find_node(child, name)
            if result:
                return result

        return None

    def get_document_count(self, root: IndexNode) -> int:
        """Get total document count in tree.

        Args:
            root: Root node

        Returns:
            Total document count
        """
        return root.doc_count

    def print_tree(self, node: IndexNode, indent: int = 0) -> None:
        """Print tree structure to logger.

        Args:
            node: Node to print
            indent: Indentation level
        """
        prefix = "  " * indent
        summary = f" - {node.summary[:50]}..." if node.summary else ""
        logger.info(f"{prefix}{node.name} ({node.type}){summary}")

        for child in node.children:
            self.print_tree(child, indent + 1)
