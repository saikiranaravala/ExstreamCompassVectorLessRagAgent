"""OCR module for scanned documents using pytesseract."""

import io
import logging
from typing import Optional

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Process scanned documents using OCR."""

    # Tesseract configuration
    TESSERACT_CONFIG = r"--oem 3 --psm 6"

    @staticmethod
    def is_tesseract_available() -> bool:
        """Check if Tesseract is installed and available.

        Returns:
            True if Tesseract is available
        """
        try:
            pytesseract.get_tesseract_version()
            return True
        except pytesseract.TesseractNotFoundError:
            logger.warning("Tesseract not found. OCR functionality disabled.")
            return False

    @staticmethod
    def extract_text_from_image(image: Image.Image) -> str:
        """Extract text from image using OCR.

        Args:
            image: PIL Image object

        Returns:
            Extracted text
        """
        if not OCRProcessor.is_tesseract_available():
            logger.warning("Tesseract not available for OCR")
            return ""

        try:
            text = pytesseract.image_to_string(
                image,
                config=OCRProcessor.TESSERACT_CONFIG,
            )
            return text.strip()
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

    @staticmethod
    def extract_text_from_bytes(image_bytes: bytes) -> str:
        """Extract text from image bytes using OCR.

        Args:
            image_bytes: Image content as bytes

        Returns:
            Extracted text
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            return OCRProcessor.extract_text_from_image(image)
        except Exception as e:
            logger.error(f"Failed to open image from bytes: {e}")
            return ""

    @staticmethod
    def preprocess_image(image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy.

        Args:
            image: PIL Image object

        Returns:
            Preprocessed image
        """
        try:
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Resize if too small (Tesseract performs better on larger images)
            width, height = image.size
            if width < 300 or height < 300:
                scale = max(300 / width, 300 / height)
                new_size = (int(width * scale), int(height * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Enhance contrast
            from PIL import ImageEnhance

            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)

            return image
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image

    @staticmethod
    def extract_text_from_image_with_preprocessing(image: Image.Image) -> str:
        """Extract text from image with preprocessing for better accuracy.

        Args:
            image: PIL Image object

        Returns:
            Extracted text
        """
        try:
            preprocessed = OCRProcessor.preprocess_image(image)
            return OCRProcessor.extract_text_from_image(preprocessed)
        except Exception as e:
            logger.error(f"OCR with preprocessing failed: {e}")
            return ""

    @staticmethod
    def detect_text_density(image: Image.Image) -> float:
        """Estimate if image is likely to contain text (scanned vs blank).

        Args:
            image: PIL Image object

        Returns:
            Text density score (0.0 to 1.0)
        """
        try:
            # Convert to grayscale
            gray = image.convert("L") if image.mode != "L" else image

            # Calculate pixel variance - text-heavy images have higher variance
            pixels = list(gray.getdata())
            if not pixels:
                return 0.0

            mean = sum(pixels) / len(pixels)
            variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)

            # Normalize variance to 0-1 scale
            max_variance = 127 ** 2  # Max variance for 8-bit images
            density = min(1.0, variance / max_variance)

            return density
        except Exception as e:
            logger.warning(f"Text density detection failed: {e}")
            return 0.5


class PDFPageOCR:
    """OCR support for PDF pages (requires pdf2image conversion)."""

    @staticmethod
    def extract_text_from_pdf_page(
        page_image: Image.Image, use_preprocessing: bool = True
    ) -> str:
        """Extract text from a PDF page image using OCR.

        Args:
            page_image: PIL Image of a PDF page
            use_preprocessing: Whether to preprocess image first

        Returns:
            Extracted text
        """
        if not OCRProcessor.is_tesseract_available():
            return ""

        if use_preprocessing:
            return OCRProcessor.extract_text_from_image_with_preprocessing(page_image)
        else:
            return OCRProcessor.extract_text_from_image(page_image)

    @staticmethod
    def should_use_ocr(page_image: Image.Image, threshold: float = 0.3) -> bool:
        """Determine if OCR should be used for this page.

        Args:
            page_image: PIL Image of a PDF page
            threshold: Text density threshold (use OCR if below this)

        Returns:
            True if OCR is recommended
        """
        density = OCRProcessor.detect_text_density(page_image)
        return density < threshold
