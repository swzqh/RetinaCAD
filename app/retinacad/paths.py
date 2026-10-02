"""Resolve resources in source and frozen application layouts."""

from __future__ import annotations

import sys
from pathlib import Path


def handoff_root() -> Path:
    """Return the repository root when running from source."""
    return Path(__file__).resolve().parents[2]


def resource_path(relative: str | Path) -> Path:
    """Resolve a bundled resource for source or PyInstaller execution."""
    relative = Path(relative)
    candidates: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / relative)
    candidates.append(Path(__file__).resolve().parents[1] / relative)
    candidates.append(handoff_root() / relative)
    candidates.append(Path(sys.executable).resolve().parent / relative)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def model_path() -> Path:
    """Return the locked A3 model JSON path."""
    return resource_path("model/A3_locked_model.json")
