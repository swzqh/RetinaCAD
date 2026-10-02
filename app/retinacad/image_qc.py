"""Offline technical checks for uploaded fundus photographs."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
MAX_FILE_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class QCItem:
    """One technical image check."""

    name: str
    value: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ImageQCResult:
    """Technical image metadata and advisory checks."""

    path: Path
    width: int
    height: int
    mode: str
    brightness: float
    contrast: float
    edge_strength: float
    dark_fraction: float
    saturated_fraction: float
    items: tuple[QCItem, ...]

    @property
    def needs_review(self) -> bool:
        return any(not item.passed for item in self.items)


def analyze_image(path: str | Path) -> ImageQCResult:
    """Run conservative, non-diagnostic technical checks on one image."""
    image_path = Path(path)
    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Supported formats are JPG, PNG, and TIF/TIFF")
    if image_path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Image file exceeds 100 MB")

    try:
        with Image.open(image_path) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
            width, height = image.size
            sample = image.copy()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The image cannot be decoded or is damaged") from exc

    if width < 64 or height < 64:
        raise ValueError("Image dimensions are too small for analysis")

    sample.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(sample)
    stats = ImageStat.Stat(gray)
    brightness = float(stats.mean[0])
    contrast = float(stats.stddev[0])

    edge = gray.filter(ImageFilter.FIND_EDGES)
    border = max(2, int(min(edge.size) * 0.03))
    if edge.width > border * 2 and edge.height > border * 2:
        edge = ImageOps.crop(edge, border=border)
    edge_strength = float(ImageStat.Stat(edge).stddev[0])

    histogram = gray.histogram()
    total = max(1, sum(histogram))
    dark_fraction = sum(histogram[:20]) / total
    saturated_fraction = sum(histogram[246:]) / total

    min_side = min(width, height)
    items = (
        QCItem(
            "Resolution",
            f"{width} × {height}",
            min_side >= 800,
            "A minimum short side of 800 px is recommended",
        ),
        QCItem(
            "Brightness",
            f"{brightness:.0f} / 255",
            35 <= brightness <= 220,
            "Technical screening for under- or overexposure only",
        ),
        QCItem(
            "Contrast",
            f"{contrast:.1f}",
            contrast >= 28,
            "Low contrast may affect vessel segmentation",
        ),
        QCItem(
            "Edge detail",
            f"{edge_strength:.1f}",
            edge_strength >= 12,
            "Low values require manual review for blur",
        ),
    )
    return ImageQCResult(
        path=image_path,
        width=width,
        height=height,
        mode="RGB",
        brightness=brightness,
        contrast=contrast,
        edge_strength=edge_strength,
        dark_fraction=dark_fraction,
        saturated_fraction=saturated_fraction,
        items=items,
    )
