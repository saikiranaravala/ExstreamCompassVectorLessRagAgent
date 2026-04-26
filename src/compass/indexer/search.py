"""BM25 lexical search index using tantivy."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import tantivy

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from a search query."""

    doc_id: str
    title: str
    path: str
    score: float
    content_preview: str


class BM25Index:
    """BM25 full-text search index using tantivy."""

    def __init__(self, index_path: Path):
        """Initialize or open BM25 index.

        Args:
            index_path: Path to store index files
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.schema = self._create_schema()
        self.index = self._open_or_create_index()

    def _create_schema(self) -> tantivy.Schema:
        """Create tantivy schema for documents.

        Returns:
            tantivy Schema
        """
        schema_builder = tantivy.SchemaBuilder()

        # Field definitions
        schema_builder.add_text_field("doc_id", stored=True)
        schema_builder.add_text_field("title", stored=True, tokenizer_name="en_stem")
        schema_builder.add_text_field("path", stored=True)
        schema_builder.add_text_field("content", tokenizer_name="en_stem")
        schema_builder.add_text_field(
            "content_preview", stored=True, tokenizer_name="en_stem"
        )
        schema_builder.add_u64_field("timestamp", stored=True)

        return schema_builder.build()

    def _open_or_create_index(self) -> tantivy.Index:
        """Open existing index or create new one.

        Returns:
            tantivy Index
        """
        index_file = self.index_path / "index.tan"

        try:
            if index_file.exists():
                logger.info(f"Opening existing index at {self.index_path}")
                return tantivy.Index(self.schema, str(index_file))
            else:
                logger.info(f"Creating new index at {self.index_path}")
                return tantivy.Index(self.schema, str(index_file))
        except Exception as e:
            logger.error(f"Failed to open/create index: {e}")
            # Create fresh index
            return tantivy.Index(self.schema, str(index_file))

    def add_document(
        self,
        doc_id: str,
        title: str,
        path: str,
        content: str,
        timestamp: int,
    ) -> bool:
        """Add a document to the index.

        Args:
            doc_id: Unique document identifier
            title: Document title
            path: Document path or URL
            content: Full document content
            timestamp: Unix timestamp of indexing

        Returns:
            True if successful, False otherwise
        """
        try:
            writer = self.index.writer()

            # Create preview (first 200 chars)
            preview = content[:200].strip()

            writer.add_document(
                tantivy.Document(
                    doc_id=doc_id,
                    title=title,
                    path=path,
                    content=content,
                    content_preview=preview,
                    timestamp=timestamp,
                )
            )

            writer.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")
            return False

    def batch_add_documents(self, documents: list[dict]) -> int:
        """Add multiple documents to index.

        Args:
            documents: List of document dicts with keys:
                - doc_id, title, path, content, timestamp

        Returns:
            Number of documents successfully added
        """
        try:
            writer = self.index.writer()
            added_count = 0

            for doc in documents:
                try:
                    preview = doc["content"][:200].strip()
                    writer.add_document(
                        tantivy.Document(
                            doc_id=doc["doc_id"],
                            title=doc["title"],
                            path=doc["path"],
                            content=doc["content"],
                            content_preview=preview,
                            timestamp=doc.get("timestamp", 0),
                        )
                    )
                    added_count += 1
                except Exception as e:
                    logger.warning(f"Failed to add document {doc.get('doc_id')}: {e}")

            writer.commit()
            logger.info(f"Added {added_count}/{len(documents)} documents to index")
            return added_count
        except Exception as e:
            logger.error(f"Batch add failed: {e}")
            return 0

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search the index.

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of SearchResult objects
        """
        try:
            searcher = self.index.searcher()
            query_obj = self.index.parse_query(query, ["title", "content"])

            results = searcher.search(query_obj, limit=limit)
            search_results = []

            for score, doc_address in results:
                doc = searcher.doc(doc_address)

                search_results.append(
                    SearchResult(
                        doc_id=doc.get_first("doc_id").text() if doc.get_first("doc_id") else "",
                        title=doc.get_first("title").text() if doc.get_first("title") else "",
                        path=doc.get_first("path").text() if doc.get_first("path") else "",
                        score=float(score),
                        content_preview=doc.get_first("content_preview").text()
                        if doc.get_first("content_preview")
                        else "",
                    )
                )

            return search_results
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the index.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if successful
        """
        try:
            writer = self.index.writer()
            writer.delete_query(
                self.index.parse_query(f'doc_id:"{doc_id}"', ["doc_id"])
            )
            writer.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    def get_document_count(self) -> int:
        """Get total document count in index.

        Returns:
            Number of indexed documents
        """
        try:
            searcher = self.index.searcher()
            return searcher.num_docs
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0

    def clear_index(self) -> bool:
        """Clear all documents from index.

        Returns:
            True if successful
        """
        try:
            writer = self.index.writer()
            # Delete all documents by searching for any text
            writer.delete_query(self.index.parse_query("*", ["content"]))
            writer.commit()
            logger.info("Index cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False
