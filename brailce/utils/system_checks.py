"""
Brailce Utility – System Checks
==================================

Runtime checks for system dependencies (Piper TTS, Ollama, etc.).
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class SystemCheck:
    """Result of a single system dependency check."""
    name: str
    available: bool
    version: str = ""
    message: str = ""


def check_piper(model_path: str | None = None) -> SystemCheck:
    """Check for Piper runtime and the configured ONNX model and sidecar."""
    configured_model = model_path or "~/piper/en_US-ryan-medium.onnx"
    model = Path(os.path.expandvars(os.path.expanduser(configured_model)))
    model_config = Path(f"{model}.json")
    runtime_available = bool(shutil.which("piper"))
    home = Path.home()
    runtime_candidates = (
        home / "piper" / "piper" / "piper",
        home / "piper" / "piper" / "piper.exe",
        Path("/usr/local/bin/piper"),
        Path("/usr/bin/piper"),
    )
    runtime_available = runtime_available or any(
        candidate.is_file() for candidate in runtime_candidates
    )
    if not runtime_available:
        try:
            from piper import PiperVoice  # noqa: F401
            runtime_available = True
        except ImportError:
            runtime_available = False

    missing = []
    if not model.is_file():
        missing.append(f"model file missing: {model}")
    if not model_config.is_file():
        missing.append(f"model config missing: {model_config}")
    if not runtime_available:
        missing.append("Piper CLI or piper-tts Python package missing")
    return SystemCheck(
        name="Piper TTS",
        available=not missing,
        message="; ".join(missing) if missing else f"Using {model}",
    )


def check_ollama(host: str = "http://127.0.0.1:11434") -> SystemCheck:
    """Check if Ollama is running and accessible."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return SystemCheck(
                    name="Ollama",
                    available=True,
                    message=f"Connected to {host}",
                )
    except Exception as exc:
        return SystemCheck(
            name="Ollama",
            available=False,
            message=f"Cannot reach Ollama at {host}: {exc}",
        )

    return SystemCheck(
        name="Ollama",
        available=False,
        message=f"Ollama not responding at {host}",
    )


def run_all_checks(
    ollama_host: str = "http://127.0.0.1:11434",
    piper_model_path: str | None = None,
) -> List[SystemCheck]:
    """Run all system dependency checks and return results."""
    checks = [
        check_piper(piper_model_path),
        check_ollama(ollama_host),
    ]

    for check in checks:
        level = logging.INFO if check.available else logging.WARNING
        logger.log(
            level,
            "System check [%s]: %s — %s",
            check.name,
            "OK" if check.available else "MISSING",
            check.message,
        )

    return checks
