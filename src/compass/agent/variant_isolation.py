"""Variant isolation and enforcement logic."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VariantConfig:
    """Configuration for a documentation variant."""

    name: str  # "CloudNative" or "ServerBased"
    root_path: str
    allowed_prefixes: list[str]
    description: str


class VariantIsolationManager:
    """Manage variant isolation and enforce boundaries."""

    # Predefined variants
    CLOUDNATIVE = VariantConfig(
        name="CloudNative",
        root_path="docs/CloudNative",
        allowed_prefixes=["docs/CloudNative/", "CloudNative/"],
        description="Cloud-native Exstream documentation",
    )

    SERVERBASED = VariantConfig(
        name="ServerBased",
        root_path="docs/ServerBased",
        allowed_prefixes=[
            "docs/ServerBased/",
            "ServerBased/",
            "CommunicationsDesigner/",
            "ContentAuthor/",
            "DesignAndProduction/",
            "Empower/",
        ],
        description="Server-based Exstream documentation",
    )

    OTDS = VariantConfig(
        name="OTDS_DirectoryServices",
        root_path="docs/OTDS_DirectoryServices",
        allowed_prefixes=["docs/OTDS_DirectoryServices/", "OTDS_DirectoryServices/"],
        description="OpenText Directory Services documentation",
    )

    def __init__(self, docs_root: Optional[Path] = None):
        """Initialize variant manager.

        Args:
            docs_root: Root documentation directory
        """
        self.docs_root = Path(docs_root) if docs_root else Path("docs")
        self.variants = {
            "CloudNative": self.CLOUDNATIVE,
            "ServerBased": self.SERVERBASED,
            "OTDS_DirectoryServices": self.OTDS,
        }

    def validate_variant(self, variant: str) -> bool:
        """Validate that variant exists.

        Args:
            variant: Variant name

        Returns:
            True if valid variant
        """
        return variant in self.variants

    def get_variant(self, variant: str) -> Optional[VariantConfig]:
        """Get variant configuration.

        Args:
            variant: Variant name

        Returns:
            VariantConfig or None
        """
        return self.variants.get(variant)

    def is_path_in_variant(self, path: str, variant: str) -> bool:
        """Check if path belongs to variant.

        Args:
            path: File or folder path
            variant: Variant name

        Returns:
            True if path is in variant
        """
        if not self.validate_variant(variant):
            logger.warning(f"Invalid variant: {variant}")
            return False

        variant_config = self.variants[variant]

        # Normalize path
        path_lower = path.lower().replace("\\", "/")

        # Check against allowed prefixes
        for prefix in variant_config.allowed_prefixes:
            if path_lower.startswith(prefix.lower()):
                return True

        return False

    def enforce_variant_path(self, path: str, variant: str) -> Optional[str]:
        """Enforce variant constraints on a path.

        Returns the valid path or None if not allowed.

        Args:
            path: Requested file path
            variant: Variant constraint

        Returns:
            Valid path or None if not allowed
        """
        if not self.is_path_in_variant(path, variant):
            logger.warning(
                f"Path '{path}' not allowed for variant '{variant}'"
            )
            return None

        return path

    def filter_search_results(
        self,
        results: list[dict],
        variant: str,
    ) -> list[dict]:
        """Filter search results to only include variant-appropriate items.

        Args:
            results: Search results with 'path' field
            variant: Variant constraint

        Returns:
            Filtered results
        """
        if not self.validate_variant(variant):
            logger.warning(f"Invalid variant: {variant}")
            return []

        filtered = []
        for result in results:
            path = result.get("path", "")
            if self.is_path_in_variant(path, variant):
                filtered.append(result)
            else:
                logger.debug(
                    f"Filtered out result: {path} (not in {variant})"
                )

        return filtered

    def get_variant_root(self, variant: str) -> Optional[Path]:
        """Get root path for variant.

        Args:
            variant: Variant name

        Returns:
            Root path or None if invalid
        """
        if not self.validate_variant(variant):
            return None

        variant_config = self.variants[variant]
        return self.docs_root / variant_config.root_path.replace("docs/", "")

    def list_variants(self) -> list[dict]:
        """List available variants.

        Returns:
            List of variant info dicts
        """
        return [
            {
                "name": config.name,
                "description": config.description,
                "root": config.root_path,
            }
            for config in self.variants.values()
        ]


class VariantEnforcer:
    """Enforce variant constraints on tool execution."""

    def __init__(self, isolation_manager: VariantIsolationManager):
        """Initialize enforcer.

        Args:
            isolation_manager: VariantIsolationManager instance
        """
        self.manager = isolation_manager

    def can_read_document(self, doc_path: str, variant: str) -> bool:
        """Check if document can be read in variant context.

        Args:
            doc_path: Path to document
            variant: Active variant

        Returns:
            True if read is allowed
        """
        return self.manager.is_path_in_variant(doc_path, variant)

    def can_search_variant(self, query: str, variant: str) -> bool:
        """Check if search query is allowed for variant.

        Args:
            query: Search query
            variant: Active variant

        Returns:
            True if search is allowed
        """
        # Currently allow all searches, but filter results
        return self.manager.validate_variant(variant)

    def enforce_tool_call(
        self,
        tool_name: str,
        tool_args: dict,
        variant: str,
    ) -> bool:
        """Validate tool call against variant constraints.

        Args:
            tool_name: Name of tool being called
            tool_args: Tool arguments
            variant: Active variant

        Returns:
            True if call is allowed
        """
        if tool_name == "read_html" or tool_name == "read_pdf":
            file_path = tool_args.get("file_path", "")
            return self.can_read_document(file_path, variant)

        if tool_name == "lexical_search":
            return self.can_search_variant(tool_args.get("query", ""), variant)

        if tool_name == "list_node":
            node_path = tool_args.get("node_path", "")
            return self.can_read_document(node_path, variant)

        if tool_name == "compare_variants":
            # This tool explicitly compares variants, so allow it
            return True

        # Default: allow unknown tools (for extensibility)
        return True

    def filter_tool_output(
        self,
        tool_name: str,
        output: dict,
        variant: str,
    ) -> dict:
        """Filter tool output to enforce variant boundaries.

        Args:
            tool_name: Tool that produced output
            output: Tool output
            variant: Active variant

        Returns:
            Filtered output
        """
        if tool_name == "lexical_search" and "results" in output:
            # Filter search results to variant
            output["results"] = self.manager.filter_search_results(
                output["results"],
                variant,
            )

        if tool_name == "list_node" and "children" in output:
            # Filter listed children to variant
            children = output.get("children", [])
            filtered_children = [
                child for child in children
                if self.manager.is_path_in_variant(
                    child.get("path", ""),
                    variant,
                )
            ]
            output["children"] = filtered_children

        return output

    def validate_answer(self, answer: str, variant: str) -> bool:
        """Validate that answer doesn't contain cross-variant info.

        Args:
            answer: Generated answer
            variant: Active variant

        Returns:
            True if answer is valid (not a strict validation, mainly for logging)
        """
        # Check for variant-specific terms that shouldn't appear
        if variant == "CloudNative":
            # ServerBased-specific terms shouldn't appear in CloudNative answer
            forbidden_terms = ["serverbased", "server-based", "on-premise"]
            for term in forbidden_terms:
                if term.lower() in answer.lower():
                    logger.warning(
                        f"Answer contains forbidden term for {variant}: {term}"
                    )
                    return False

        elif variant == "ServerBased":
            # CloudNative-specific terms shouldn't appear in ServerBased answer
            forbidden_terms = ["cloud", "kubernetes", "saas"]
            for term in forbidden_terms:
                if term.lower() in answer.lower():
                    logger.warning(
                        f"Answer contains forbidden term for {variant}: {term}"
                    )
                    # Note: we still allow it, just log warning

        return True
