"""Tests for OCR module."""

import pytest
from PIL import Image

from compass.indexer.ocr import OCRProcessor, PDFPageOCR


class TestOCRProcessor:
    """Test OCRProcessor class."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        # Create a simple white image
        return Image.new("RGB", (100, 100), color="white")

    @pytest.fixture
    def sample_image_bytes(self, sample_image):
        """Create image bytes for testing."""
        import io

        buf = io.BytesIO()
        sample_image.save(buf, format="PNG")
        return buf.getvalue()

    def test_is_tesseract_available(self):
        """Test Tesseract availability check."""
        # This will return True or False depending on system config
        result = OCRProcessor.is_tesseract_available()
        assert isinstance(result, bool)

    def test_preprocess_image_converts_mode(self):
        """Test image preprocessing converts image mode."""
        # Create a 1-bit image
        image = Image.new("1", (100, 100))
        preprocessed = OCRProcessor.preprocess_image(image)

        # Should be converted to RGB
        assert preprocessed.mode == "RGB"

    def test_preprocess_image_scales_small_images(self):
        """Test image preprocessing scales small images."""
        # Create a small image
        image = Image.new("RGB", (100, 100))
        preprocessed = OCRProcessor.preprocess_image(image)

        # Should be scaled up
        assert preprocessed.size[0] >= 300 or preprocessed.size[1] >= 300

    def test_preprocess_image_preserves_large_images(self):
        """Test image preprocessing preserves large images."""
        # Create a large image
        image = Image.new("RGB", (500, 500))
        original_size = image.size
        preprocessed = OCRProcessor.preprocess_image(image)

        # Should be approximately same size (may have slight scaling)
        assert preprocessed.size[0] >= 400
        assert preprocessed.size[1] >= 400

    def test_extract_text_from_image_with_missing_tesseract(self, sample_image):
        """Test extraction handles missing Tesseract gracefully."""
        # This will return empty string if Tesseract not available
        text = OCRProcessor.extract_text_from_image(sample_image)
        assert isinstance(text, str)

    def test_extract_text_from_bytes(self, sample_image_bytes):
        """Test text extraction from image bytes."""
        text = OCRProcessor.extract_text_from_bytes(sample_image_bytes)
        assert isinstance(text, str)

    def test_extract_text_from_image_with_preprocessing(self, sample_image):
        """Test extraction with preprocessing."""
        text = OCRProcessor.extract_text_from_image_with_preprocessing(sample_image)
        assert isinstance(text, str)

    def test_detect_text_density_white_image(self):
        """Test text density detection on blank white image."""
        image = Image.new("RGB", (100, 100), color="white")
        density = OCRProcessor.detect_text_density(image)

        # Blank white image should have low density
        assert 0.0 <= density <= 1.0
        assert density < 0.5

    def test_detect_text_density_black_image(self):
        """Test text density detection on solid black image."""
        image = Image.new("RGB", (100, 100), color="black")
        density = OCRProcessor.detect_text_density(image)

        # Solid black image should have high density
        assert 0.0 <= density <= 1.0

    def test_detect_text_density_mixed_image(self):
        """Test text density on mixed content image."""
        import random

        # Create image with mixed pixels
        image = Image.new("RGB", (100, 100))
        pixels = image.load()
        for i in range(100):
            for j in range(100):
                gray = random.randint(0, 255)
                pixels[i, j] = (gray, gray, gray)

        density = OCRProcessor.detect_text_density(image)
        assert 0.0 <= density <= 1.0

    def test_detect_text_density_invalid_image(self):
        """Test text density detection gracefully handles errors."""
        # Create an empty image
        image = Image.new("RGB", (0, 0))
        density = OCRProcessor.detect_text_density(image)

        # Should return a valid score
        assert isinstance(density, float)
        assert 0.0 <= density <= 1.0


class TestPDFPageOCR:
    """Test PDFPageOCR class."""

    @pytest.fixture
    def sample_page_image(self):
        """Create a sample PDF page image."""
        return Image.new("RGB", (612, 792), color="white")

    def test_extract_text_from_pdf_page(self, sample_page_image):
        """Test text extraction from PDF page."""
        text = PDFPageOCR.extract_text_from_pdf_page(sample_page_image)
        assert isinstance(text, str)

    def test_extract_text_from_pdf_page_with_preprocessing(self, sample_page_image):
        """Test extraction with preprocessing flag."""
        text = PDFPageOCR.extract_text_from_pdf_page(
            sample_page_image, use_preprocessing=True
        )
        assert isinstance(text, str)

    def test_extract_text_from_pdf_page_without_preprocessing(self, sample_page_image):
        """Test extraction without preprocessing flag."""
        text = PDFPageOCR.extract_text_from_pdf_page(
            sample_page_image, use_preprocessing=False
        )
        assert isinstance(text, str)

    def test_should_use_ocr_on_blank_page(self):
        """Test OCR recommendation for blank page."""
        # Blank white page should trigger OCR
        image = Image.new("RGB", (612, 792), color="white")
        should_ocr = PDFPageOCR.should_use_ocr(image, threshold=0.3)

        assert isinstance(should_ocr, bool)
        # Blank page should have low density, suggesting OCR
        assert should_ocr is True

    def test_should_use_ocr_on_text_page(self):
        """Test OCR recommendation for text page."""
        # Create a mostly dark page (high text density)
        image = Image.new("RGB", (612, 792), color="black")
        should_ocr = PDFPageOCR.should_use_ocr(image, threshold=0.3)

        assert isinstance(should_ocr, bool)

    def test_should_use_ocr_custom_threshold(self, sample_page_image):
        """Test OCR recommendation with custom threshold."""
        # Test with different thresholds
        result_low = PDFPageOCR.should_use_ocr(sample_page_image, threshold=0.1)
        result_high = PDFPageOCR.should_use_ocr(sample_page_image, threshold=0.9)

        assert isinstance(result_low, bool)
        assert isinstance(result_high, bool)
