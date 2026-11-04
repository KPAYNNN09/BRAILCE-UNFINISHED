"""
Brailce Utility – Path Management
====================================

Provides consistent path resolution for project files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """
    Return the project root directory.

    Walks up from this file to find the directory containing main.py.
    Falls back to the current working directory.
    """
    # This file is at brailce/utils/paths.py
    # Project root contains brailce/ and main.py
    current = Path(__file__).resolve().parent
    for _ in range(5):  # Walk up at most 5 levels
        candidate = current.parent
        if (candidate / "main.py").exists() or (candidate / "brailce").is_dir():
            return candidate
        current = candidate
    return Path.cwd()


def resolve_path(relative_path: str) -> Path:
    """
    Resolve a path relative to the project root.

    Args:
        relative_path: Path relative to the project root.

    Returns:
        Absolute Path object.
    """
    return get_project_root() / relative_path


def ensure_directory(directory: Path) -> Path:
    """
    Create a directory (and parents) if it does not exist.

    Returns:
        The directory Path.
    """
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_log_directory() -> Path:
    """Return the logs directory, creating it if necessary."""
    log_dir = get_project_root() / "logs"
    return ensure_directory(log_dir)


def get_mapping_directory() -> Path:
    """Return the Braille mappings directory."""
    return get_project_root() / "brailce" / "braille" / "mappings"
