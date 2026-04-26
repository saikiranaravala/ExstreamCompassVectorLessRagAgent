"""Vision service for diagram and figure interpretation."""

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)


@dataclass
class Figure:
    """A figure extracted from a document."""

    doc_id: str
    path: str
    page: Optional[int] = None
    type: str = "image"  # "diagram", "chart", "image", "table"
    description: Optional[str] = None
    caption: Optional[str] = None
    confidence: float = 0.0


@dataclass
class VisionAnalysis:
    """Result of vision analysis on a figure."""

    figure_id: str
    interpretation: str
    objects_detected: list[str]
    key_insights: list[str]
    confidence: float = 0.0
    model: str = "claude-opus-4-7"


class FigureExtractor:
    """Extract figures and diagrams from documents."""

    # Supported image formats
    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

    @staticmethod
    def extract_from_file(file_path: Path) -> Optional[Figure]:
        """Extract figure information from file.

        Args:
            file_path: Path to figure file

        Returns:
            Figure or None if not a valid image
        """
        try:
            file_path = Path(file_path)

            if file_path.suffix.lower() not in FigureExtractor.SUPPORTED_FORMATS:
                logger.warning(f"Unsupported image format: {file_path.suffix}")
                return None

            if not file_path.exists():
                logger.warning(f"Figure file not found: {file_path}")
                return None

            return Figure(
                doc_id=file_path.stem,
                path=str(file_path),
                type=FigureExtractor._detect_type(file_path),
            )

        except Exception as e:
            logger.error(f"Failed to extract figure: {e}")
            return None

    @staticmethod
    def _detect_type(file_path: Path) -> str:
        """Detect figure type from name/context.

        Args:
            file_path: Path to figure

        Returns:
            Figure type
        """
        name_lower = file_path.name.lower()

        if "diagram" in name_lower or "flow" in name_lower:
            return "diagram"
        elif "chart" in name_lower or "graph" in name_lower:
            return "chart"
        elif "table" in name_lower:
            return "table"
        else:
            return "image"

    @staticmethod
    def extract_from_directory(dir_path: Path) -> list[Figure]:
        """Extract all figures from directory.

        Args:
            dir_path: Directory containing figures

        Returns:
            List of extracted figures
        """
        figures = []
        dir_path = Path(dir_path)

        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return figures

        for file_path in dir_path.iterdir():
            if file_path.is_file():
                figure = FigureExtractor.extract_from_file(file_path)
                if figure:
                    figures.append(figure)

        logger.info(f"Extracted {len(figures)} figures from {dir_path}")
        return figures


class VisionInterpreter:
    """Interpret diagrams and figures using Claude vision."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-7"):
        """Initialize vision interpreter.

        Args:
            api_key: Anthropic API key
            model: Claude model to use for vision
        """
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model = model
        self.cache = {}

    def interpret_figure(
        self,
        figure: Figure,
        max_tokens: int = 1024,
    ) -> Optional[VisionAnalysis]:
        """Interpret a figure using vision.

        Args:
            figure: Figure to interpret
            max_tokens: Maximum tokens for response

        Returns:
            VisionAnalysis or None if interpretation failed
        """
        # Check cache
        if figure.doc_id in self.cache:
            logger.debug(f"Using cached interpretation for {figure.doc_id}")
            return self.cache[figure.doc_id]

        try:
            # Read image file
            image_path = Path(figure.path)
            if not image_path.exists():
                logger.warning(f"Image file not found: {figure.path}")
                return None

            with open(image_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            # Determine media type
            suffix = image_path.suffix.lower()
            media_type_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            media_type = media_type_map.get(suffix, "image/jpeg")

            # Build prompt based on figure type
            prompt = self._build_prompt(figure)

            # Call Claude with vision
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            interpretation_text = message.content[0].text

            # Parse response
            analysis = VisionAnalysis(
                figure_id=figure.doc_id,
                interpretation=interpretation_text,
                objects_detected=self._extract_objects(interpretation_text),
                key_insights=self._extract_insights(interpretation_text),
                confidence=0.85,  # Vision interpretation confidence
                model=self.model,
            )

            # Cache result
            self.cache[figure.doc_id] = analysis

            logger.info(f"Interpreted figure: {figure.doc_id}")
            return analysis

        except Exception as e:
            logger.error(f"Failed to interpret figure {figure.doc_id}: {e}")
            return None

    def _build_prompt(self, figure: Figure) -> str:
        """Build interpretation prompt based on figure type.

        Args:
            figure: Figure to interpret

        Returns:
            Prompt string
        """
        base_prompt = f"""Analyze this {figure.type} from technical documentation.

Provide:
1. Clear description of what the {figure.type} shows
2. Key components or elements visible
3. Main insights or information conveyed
4. How this relates to system architecture or workflows
5. Important details for someone learning from the documentation

Be specific and technical."""

        if figure.type == "diagram":
            return base_prompt + "\n\nFocus on the flow, relationships, and system components shown."

        elif figure.type == "chart":
            return base_prompt + "\n\nFocus on data trends, comparisons, and numerical insights."

        elif figure.type == "table":
            return base_prompt + "\n\nFocus on data organization, column meanings, and key rows."

        else:
            return base_prompt

    @staticmethod
    def _extract_objects(text: str) -> list[str]:
        """Extract detected objects from interpretation.

        Args:
            text: Interpretation text

        Returns:
            List of objects
        """
        objects = []

        # Simple heuristic: look for capitalized nouns
        words = text.split()
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 3:
                # Remove punctuation
                clean_word = word.rstrip(".,;:")
                if clean_word and not clean_word.startswith(("The", "A", "An")):
                    objects.append(clean_word)

        return list(dict.fromkeys(objects))[:10]  # Deduplicate and limit

    @staticmethod
    def _extract_insights(text: str) -> list[str]:
        """Extract key insights from interpretation.

        Args:
            text: Interpretation text

        Returns:
            List of insights
        """
        insights = []
        sentences = text.split(".")

        for sentence in sentences[:5]:  # First 5 sentences
            sentence = sentence.strip()
            if len(sentence) > 20 and sentence:
                insights.append(sentence)

        return insights


class VisionCache:
    """Cache for vision interpretations."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize vision cache.

        Args:
            cache_dir: Directory to store cache
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(".vision_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache = {}

    def get(self, figure_id: str) -> Optional[VisionAnalysis]:
        """Get cached analysis.

        Args:
            figure_id: Figure identifier

        Returns:
            VisionAnalysis or None
        """
        # Check memory cache first
        if figure_id in self.memory_cache:
            return self.memory_cache[figure_id]

        # Check disk cache
        cache_file = self.cache_dir / f"{figure_id}.json"
        if cache_file.exists():
            try:
                import json

                with open(cache_file) as f:
                    data = json.load(f)
                    analysis = VisionAnalysis(
                        figure_id=data["figure_id"],
                        interpretation=data["interpretation"],
                        objects_detected=data["objects_detected"],
                        key_insights=data["key_insights"],
                        confidence=data.get("confidence", 0.0),
                        model=data.get("model", ""),
                    )
                    # Update memory cache
                    self.memory_cache[figure_id] = analysis
                    return analysis
            except Exception as e:
                logger.warning(f"Failed to load cache for {figure_id}: {e}")

        return None

    def set(self, analysis: VisionAnalysis) -> bool:
        """Cache analysis.

        Args:
            analysis: VisionAnalysis to cache

        Returns:
            True if successful
        """
        try:
            import json

            # Memory cache
            self.memory_cache[analysis.figure_id] = analysis

            # Disk cache
            cache_file = self.cache_dir / f"{analysis.figure_id}.json"
            with open(cache_file, "w") as f:
                json.dump(
                    {
                        "figure_id": analysis.figure_id,
                        "interpretation": analysis.interpretation,
                        "objects_detected": analysis.objects_detected,
                        "key_insights": analysis.key_insights,
                        "confidence": analysis.confidence,
                        "model": analysis.model,
                    },
                    f,
                )

            return True

        except Exception as e:
            logger.error(f"Failed to cache analysis: {e}")
            return False

    def clear(self) -> bool:
        """Clear all cache.

        Returns:
            True if successful
        """
        try:
            import shutil

            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
            self.memory_cache.clear()

            return True

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
