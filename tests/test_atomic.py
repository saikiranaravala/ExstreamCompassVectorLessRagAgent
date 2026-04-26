"""Tests for atomic file operations."""

import json
import tempfile
from pathlib import Path

import pytest

from compass.indexer.atomic import AtomicDirectory, AtomicWriter


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestAtomicWriter:
    """Test AtomicWriter class."""

    def test_write_json_simple(self, temp_dir):
        """Test writing simple JSON file."""
        target = temp_dir / "test.json"
        data = {"key": "value", "number": 42}

        result = AtomicWriter.write_json(target, data)
        assert result is True
        assert target.exists()

        # Verify content
        with open(target) as f:
            read_data = json.load(f)
        assert read_data == data

    def test_write_json_creates_parent_dirs(self, temp_dir):
        """Test JSON write creates parent directories."""
        target = temp_dir / "nested" / "deep" / "path" / "file.json"
        data = {"test": "data"}

        result = AtomicWriter.write_json(target, data)
        assert result is True
        assert target.exists()
        assert target.parent.parent.parent.exists()

    def test_write_json_with_validation_pass(self, temp_dir):
        """Test JSON write with passing validation."""
        target = temp_dir / "test.json"
        data = {"value": 100}

        def validator(d):
            return "value" in d and d["value"] > 0

        result = AtomicWriter.write_json(target, data, validator=validator)
        assert result is True
        assert target.exists()

    def test_write_json_with_validation_fail(self, temp_dir):
        """Test JSON write with failing validation."""
        target = temp_dir / "test.json"
        data = {"value": -100}

        def validator(d):
            return "value" in d and d["value"] > 0

        result = AtomicWriter.write_json(target, data, validator=validator)
        assert result is False
        # File should not exist after validation failure
        assert not target.exists()

    def test_write_text_simple(self, temp_dir):
        """Test writing text file."""
        target = temp_dir / "test.txt"
        content = "Hello, World!\nLine 2\nLine 3"

        result = AtomicWriter.write_text(target, content)
        assert result is True
        assert target.exists()

        with open(target) as f:
            read_content = f.read()
        assert read_content == content

    def test_write_text_with_validation(self, temp_dir):
        """Test text write with validation."""
        target = temp_dir / "test.txt"
        content = "Valid content"

        def validator(text):
            return len(text) > 0 and "Valid" in text

        result = AtomicWriter.write_text(target, content, validator=validator)
        assert result is True

    def test_write_text_validation_fail(self, temp_dir):
        """Test text write with validation failure."""
        target = temp_dir / "test.txt"
        content = "Invalid"

        def validator(text):
            return "Valid" in text

        result = AtomicWriter.write_text(target, content, validator=validator)
        assert result is False
        assert not target.exists()

    def test_atomic_write_overwrites_existing(self, temp_dir):
        """Test atomic write overwrites existing file."""
        target = temp_dir / "test.json"

        # Write first version
        data1 = {"version": 1}
        AtomicWriter.write_json(target, data1)

        # Write second version
        data2 = {"version": 2}
        result = AtomicWriter.write_json(target, data2)
        assert result is True

        with open(target) as f:
            read_data = json.load(f)
        assert read_data["version"] == 2

    def test_atomic_write_with_complex_json(self, temp_dir):
        """Test atomic write with complex nested JSON."""
        target = temp_dir / "complex.json"
        data = {
            "users": [
                {"id": 1, "name": "Alice", "roles": ["admin", "user"]},
                {"id": 2, "name": "Bob", "roles": ["user"]},
            ],
            "metadata": {"version": "1.0", "created": "2026-04-26"},
        }

        result = AtomicWriter.write_json(target, data)
        assert result is True

        with open(target) as f:
            read_data = json.load(f)
        assert read_data == data
        assert len(read_data["users"]) == 2

    def test_read_with_fallback_primary_exists(self, temp_dir):
        """Test reading from primary file when it exists."""
        primary = temp_dir / "primary.json"
        fallback = temp_dir / "fallback.json"

        data = {"source": "primary"}
        AtomicWriter.write_json(primary, data)

        result = AtomicWriter.read_with_fallback(primary, fallback)
        assert result == data

    def test_read_with_fallback_uses_fallback(self, temp_dir):
        """Test reading from fallback when primary doesn't exist."""
        primary = temp_dir / "primary.json"
        fallback = temp_dir / "fallback.json"

        data = {"source": "fallback"}
        AtomicWriter.write_json(fallback, data)

        result = AtomicWriter.read_with_fallback(primary, fallback)
        assert result == data

    def test_read_with_fallback_both_exist_prefers_primary(self, temp_dir):
        """Test that primary is preferred when both exist."""
        primary = temp_dir / "primary.json"
        fallback = temp_dir / "fallback.json"

        AtomicWriter.write_json(primary, {"source": "primary"})
        AtomicWriter.write_json(fallback, {"source": "fallback"})

        result = AtomicWriter.read_with_fallback(primary, fallback)
        assert result["source"] == "primary"

    def test_read_with_fallback_both_missing(self, temp_dir):
        """Test reading when both primary and fallback are missing."""
        primary = temp_dir / "missing_primary.json"
        fallback = temp_dir / "missing_fallback.json"

        result = AtomicWriter.read_with_fallback(primary, fallback)
        assert result is None


class TestAtomicDirectory:
    """Test AtomicDirectory class."""

    def test_ensure_exists_creates_directory(self, temp_dir):
        """Test ensure_exists creates directory."""
        new_dir = temp_dir / "new_dir"
        result = AtomicDirectory.ensure_exists(new_dir)

        assert result is True
        assert new_dir.exists()

    def test_ensure_exists_creates_nested_dirs(self, temp_dir):
        """Test ensure_exists creates nested directories."""
        new_dir = temp_dir / "a" / "b" / "c" / "d"
        result = AtomicDirectory.ensure_exists(new_dir)

        assert result is True
        assert new_dir.exists()

    def test_ensure_exists_idempotent(self, temp_dir):
        """Test ensure_exists is idempotent."""
        new_dir = temp_dir / "dir"
        result1 = AtomicDirectory.ensure_exists(new_dir)
        result2 = AtomicDirectory.ensure_exists(new_dir)

        assert result1 is True
        assert result2 is True
        assert new_dir.exists()

    def test_atomic_replace_dir_basic(self, temp_dir):
        """Test basic directory replacement."""
        source = temp_dir / "source"
        target = temp_dir / "target"

        source.mkdir()
        (source / "file.txt").write_text("content")

        result = AtomicDirectory.atomic_replace_dir(source, target)
        assert result is True
        assert target.exists()
        assert not source.exists()
        assert (target / "file.txt").exists()

    def test_atomic_replace_dir_with_backup(self, temp_dir):
        """Test directory replacement creates backup."""
        source = temp_dir / "source"
        target = temp_dir / "target"

        # Create initial target
        target.mkdir()
        (target / "old_file.txt").write_text("old content")

        # Create source
        source.mkdir()
        (source / "new_file.txt").write_text("new content")

        result = AtomicDirectory.atomic_replace_dir(source, target)
        assert result is True
        assert target.exists()
        assert (target / "new_file.txt").exists()

        # Backup should exist
        backup = target.parent / (target.name + ".bak")
        assert backup.exists()
        assert (backup / "old_file.txt").exists()

    def test_atomic_replace_dir_source_missing(self, temp_dir):
        """Test replacement fails when source is missing."""
        source = temp_dir / "missing"
        target = temp_dir / "target"

        result = AtomicDirectory.atomic_replace_dir(source, target)
        assert result is False
