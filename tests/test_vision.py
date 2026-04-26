"""Tests for vision service."""

import tempfile
from pathlib import Path

import pytest

from compass.services.vision import (
    Figure,
    VisionAnalysis,
    FigureExtractor,
    VisionInterpreter,
    VisionCache,
)


class TestFigure:
    """Test Figure dataclass."""

    def test_create_figure(self):
        """Test creating a figure."""
        figure = Figure(
            doc_id="fig1",
            path="docs/fig1.png",
            type="diagram",
            description="System architecture",
        )

        assert figure.doc_id == "fig1"
        assert figure.type == "diagram"

    def test_figure_types(self):
        """Test different figure types."""
        types = ["diagram", "chart", "image", "table"]

        for fig_type in types:
            figure = Figure(doc_id="fig", path="fig.png", type=fig_type)
            assert figure.type == fig_type


class TestVisionAnalysis:
    """Test VisionAnalysis dataclass."""

    def test_create_analysis(self):
        """Test creating vision analysis."""
        analysis = VisionAnalysis(
            figure_id="fig1",
            interpretation="The diagram shows system components",
            objects_detected=["Component1", "Component2"],
            key_insights=["Shows architecture", "Illustrates flow"],
        )

        assert analysis.figure_id == "fig1"
        assert len(analysis.objects_detected) == 2
        assert len(analysis.key_insights) == 2


class TestFigureExtractor:
    """Test FigureExtractor class."""

    def test_supported_formats(self):
        """Test supported image formats."""
        formats = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

        assert FigureExtractor.SUPPORTED_FORMATS == formats

    def test_extract_from_file_valid(self):
        """Test extracting valid image file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dummy PNG file
            img_file = Path(tmpdir) / "diagram.png"
            img_file.write_bytes(b"PNG dummy data")

            figure = FigureExtractor.extract_from_file(img_file)

            assert figure is not None
            assert figure.doc_id == "diagram"

    def test_extract_from_file_invalid_format(self):
        """Test extracting invalid file format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "notimage.txt"
            txt_file.write_text("Not an image")

            figure = FigureExtractor.extract_from_file(txt_file)

            assert figure is None

    def test_extract_from_file_nonexistent(self):
        """Test extracting non-existent file."""
        figure = FigureExtractor.extract_from_file(Path("/nonexistent/file.png"))

        assert figure is None

    def test_detect_type_diagram(self):
        """Test detecting diagram type."""
        diagram_file = Path("/path/to/system_diagram.png")

        fig_type = FigureExtractor._detect_type(diagram_file)

        assert fig_type == "diagram"

    def test_detect_type_chart(self):
        """Test detecting chart type."""
        chart_file = Path("/path/to/performance_chart.png")

        fig_type = FigureExtractor._detect_type(chart_file)

        assert fig_type == "chart"

    def test_detect_type_table(self):
        """Test detecting table type."""
        table_file = Path("/path/to/data_table.png")

        fig_type = FigureExtractor._detect_type(table_file)

        assert fig_type == "table"

    def test_extract_from_directory(self):
        """Test extracting all figures from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create dummy image files
            (tmpdir / "fig1.png").write_bytes(b"PNG")
            (tmpdir / "fig2.jpg").write_bytes(b"JPG")
            (tmpdir / "notimage.txt").write_text("text")

            figures = FigureExtractor.extract_from_directory(tmpdir)

            assert len(figures) == 2

    def test_extract_from_nonexistent_directory(self):
        """Test extracting from non-existent directory."""
        figures = FigureExtractor.extract_from_directory(Path("/nonexistent"))

        assert figures == []


class TestVisionInterpreter:
    """Test VisionInterpreter class."""

    def test_interpreter_initialization(self):
        """Test initializing vision interpreter."""
        interpreter = VisionInterpreter()

        assert interpreter.model == "claude-opus-4-7"
        assert len(interpreter.cache) == 0

    def test_interpreter_custom_model(self):
        """Test initializing with custom model."""
        interpreter = VisionInterpreter(model="custom-model")

        assert interpreter.model == "custom-model"

    def test_build_prompt_diagram(self):
        """Test building diagram interpretation prompt."""
        interpreter = VisionInterpreter()

        figure = Figure(doc_id="fig1", path="fig.png", type="diagram")

        prompt = interpreter._build_prompt(figure)

        assert "diagram" in prompt.lower()
        assert "flow" in prompt.lower() or "relationships" in prompt.lower()

    def test_build_prompt_chart(self):
        """Test building chart interpretation prompt."""
        interpreter = VisionInterpreter()

        figure = Figure(doc_id="fig1", path="fig.png", type="chart")

        prompt = interpreter._build_prompt(figure)

        assert "chart" in prompt.lower()
        assert "trend" in prompt.lower() or "data" in prompt.lower()

    def test_extract_objects(self):
        """Test extracting objects from interpretation."""
        text = "The diagram shows System Architecture with Components like Database Server and API Gateway"

        objects = VisionInterpreter._extract_objects(text)

        assert len(objects) > 0
        assert "System" in objects or "Architecture" in objects

    def test_extract_insights(self):
        """Test extracting insights from interpretation."""
        text = "This is the first insight. This is the second insight. And a third one."

        insights = VisionInterpreter._extract_insights(text)

        assert len(insights) > 0
        assert "first" in insights[0].lower()

    def test_interpret_figure_nonexistent_file(self):
        """Test interpreting non-existent figure."""
        interpreter = VisionInterpreter()

        figure = Figure(doc_id="fig1", path="/nonexistent/fig.png")

        result = interpreter.interpret_figure(figure)

        assert result is None

    def test_interpret_figure_with_cache(self):
        """Test that interpretation is cached."""
        interpreter = VisionInterpreter()

        analysis = VisionAnalysis(
            figure_id="fig1",
            interpretation="Test interpretation",
            objects_detected=["obj1"],
            key_insights=["insight1"],
        )

        interpreter.cache["fig1"] = analysis

        # Create figure with same ID
        figure = Figure(doc_id="fig1", path="/nonexistent/fig.png")

        # Should return cached result instead of error
        result = interpreter.interpret_figure(figure)

        assert result is not None
        assert result.interpretation == "Test interpretation"


class TestVisionCache:
    """Test VisionCache class."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = VisionCache(Path(tmpdir))

            assert cache.cache_dir.exists()

    def test_cache_set_and_get(self):
        """Test setting and getting cached analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = VisionCache(Path(tmpdir))

            analysis = VisionAnalysis(
                figure_id="fig1",
                interpretation="Test",
                objects_detected=["obj1"],
                key_insights=["insight1"],
            )

            result = cache.set(analysis)

            assert result is True

            retrieved = cache.get("fig1")

            assert retrieved is not None
            assert retrieved.interpretation == "Test"

    def test_cache_memory_cache(self):
        """Test memory cache is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = VisionCache(Path(tmpdir))

            analysis = VisionAnalysis(
                figure_id="fig1",
                interpretation="Test",
                objects_detected=[],
                key_insights=[],
            )

            cache.set(analysis)

            # Get from memory cache
            retrieved = cache.get("fig1")

            assert retrieved is not None

    def test_cache_disk_persistence(self):
        """Test disk cache persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            # Save in first cache instance
            cache1 = VisionCache(cache_dir)
            analysis = VisionAnalysis(
                figure_id="fig1",
                interpretation="Persisted",
                objects_detected=["obj1"],
                key_insights=["insight1"],
            )
            cache1.set(analysis)

            # Load in second cache instance
            cache2 = VisionCache(cache_dir)
            retrieved = cache2.get("fig1")

            assert retrieved is not None
            assert retrieved.interpretation == "Persisted"

    def test_cache_nonexistent_figure(self):
        """Test getting non-existent figure from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = VisionCache(Path(tmpdir))

            result = cache.get("nonexistent")

            assert result is None

    def test_cache_clear(self):
        """Test clearing cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = VisionCache(Path(tmpdir))

            analysis = VisionAnalysis(
                figure_id="fig1",
                interpretation="Test",
                objects_detected=[],
                key_insights=[],
            )

            cache.set(analysis)

            # Clear cache
            result = cache.clear()

            assert result is True

            # Should not find it anymore
            retrieved = cache.get("fig1")

            assert retrieved is None
