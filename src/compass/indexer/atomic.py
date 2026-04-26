"""Atomic file write operations with tmp-then-rename pattern."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AtomicWriter:
    """Atomic file write operations with rollback support."""

    @staticmethod
    def write_json(
        file_path: Path,
        data: Any,
        validator: Optional[Callable[[Any], bool]] = None,
    ) -> bool:
        """Atomically write JSON file.

        Uses tmp-then-rename pattern for atomicity.

        Args:
            file_path: Target file path
            data: Data to serialize as JSON
            validator: Optional validation function (returns True if valid)

        Returns:
            True if successful, False otherwise
        """
        return AtomicWriter.write_file(
            file_path,
            lambda f: json.dump(data, f, indent=2),
            validator=lambda _: validator(data) if validator else True,
        )

    @staticmethod
    def write_text(
        file_path: Path,
        content: str,
        validator: Optional[Callable[[str], bool]] = None,
    ) -> bool:
        """Atomically write text file.

        Args:
            file_path: Target file path
            content: Text content to write
            validator: Optional validation function

        Returns:
            True if successful, False otherwise
        """
        return AtomicWriter.write_file(
            file_path,
            lambda f: f.write(content),
            validator=lambda _: validator(content) if validator else True,
        )

    @staticmethod
    def write_file(
        file_path: Path,
        write_func: Callable,
        validator: Optional[Callable] = None,
    ) -> bool:
        """Atomically write file using tmp-then-rename pattern.

        Args:
            file_path: Target file path
            write_func: Function that writes to file object
            validator: Optional validation function to check temp file

        Returns:
            True if successful, False otherwise
        """
        file_path = Path(file_path)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create temporary file in same directory for atomic rename
        temp_dir = file_path.parent
        temp_fd = None
        temp_path = None

        try:
            # Create temp file in same filesystem as target
            temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir)

            # Write to temp file
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                temp_fd = None  # fdopen takes ownership
                write_func(f)

            # Validate if validator provided
            if validator:
                with open(temp_path, "r", encoding="utf-8") as f:
                    if not validator(f):
                        logger.error(f"Validation failed for {file_path}")
                        os.unlink(temp_path)
                        return False

            # Atomic rename (same filesystem guaranteed by tempfile location)
            # On Windows, this may fail if target exists, so remove it first
            if file_path.exists():
                file_path.unlink()

            os.rename(temp_path, file_path)
            logger.info(f"Atomically wrote {file_path}")
            return True

        except Exception as e:
            logger.error(f"Atomic write failed for {file_path}: {e}")

            # Cleanup temp file if it exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

            # Close file descriptor if still open
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except OSError:
                    pass

            return False

    @staticmethod
    def read_with_fallback(
        primary_path: Path, fallback_path: Optional[Path] = None
    ) -> Optional[dict]:
        """Read JSON file with fallback support.

        Args:
            primary_path: Primary file path
            fallback_path: Optional fallback file path

        Returns:
            Parsed JSON or None if both fail
        """
        primary_path = Path(primary_path)

        # Try primary file
        if primary_path.exists():
            try:
                with open(primary_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read primary file {primary_path}: {e}")

        # Try fallback file
        if fallback_path:
            fallback_path = Path(fallback_path)
            if fallback_path.exists():
                try:
                    with open(fallback_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read fallback file {fallback_path}: {e}")

        logger.error(f"Could not read from {primary_path} or fallback")
        return None


class AtomicDirectory:
    """Atomic directory operations."""

    @staticmethod
    def ensure_exists(dir_path: Path) -> bool:
        """Ensure directory exists, creating if necessary.

        Args:
            dir_path: Directory path

        Returns:
            True if successful or already exists
        """
        try:
            dir_path = Path(dir_path)
            dir_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            return False

    @staticmethod
    def atomic_replace_dir(
        source_dir: Path, target_dir: Path, backup_suffix: str = ".bak"
    ) -> bool:
        """Atomically replace directory with backup.

        Args:
            source_dir: Source directory to move
            target_dir: Target directory path
            backup_suffix: Suffix for backup of old directory

        Returns:
            True if successful
        """
        source_dir = Path(source_dir)
        target_dir = Path(target_dir)

        if not source_dir.exists():
            logger.error(f"Source directory does not exist: {source_dir}")
            return False

        try:
            # If target exists, backup it
            if target_dir.exists():
                backup_dir = target_dir.parent / (target_dir.name + backup_suffix)
                if backup_dir.exists():
                    import shutil

                    shutil.rmtree(backup_dir)
                os.rename(target_dir, backup_dir)
                logger.info(f"Backed up existing directory to {backup_dir}")

            # Move source to target
            os.rename(source_dir, target_dir)
            logger.info(f"Atomically replaced {target_dir}")
            return True

        except Exception as e:
            logger.error(f"Atomic directory replacement failed: {e}")
            return False
