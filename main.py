#!/usr/bin/env python3
"""
Brailce – Main Entry Point
=============================

Brailce: A Portable Braille-to-Voice Assistive Device

Usage:
    python main.py
    python main.py --config path/to/config.json

The laptop keyboard simulates the dedicated character buttons
during software development. Each keyboard key press is treated
as if the user pressed the corresponding physical character button
on the Brailce keypad.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure the project root is on the Python path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 output on Windows consoles to prevent charmap encoding errors
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from brailce.config.loader import ConfigLoader, ConfigError
from brailce.core.app import BrailceApp


def setup_logging(log_level: str = "INFO") -> None:
    """Configure Python logging for the application."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="brailce",
        description=(
            "Brailce: A Portable Braille-to-Voice Assistive Device. "
            "The laptop keyboard simulates dedicated character buttons "
            "during development."
        ),
    )
    parser.add_argument(
        "--config",
        type=str,
        default="brailce/config/config.json",
        help="Path to the configuration JSON file.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug-level logging.",
    )
    return parser.parse_args()


def main() -> int:
    """Application entry point."""
    args = parse_args()

    # ---- Logging ----
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(log_level)

    logger = logging.getLogger("brailce.main")
    logger.info("=" * 60)
    logger.info("  Brailce – A Portable Braille-to-Voice Assistive Device")
    logger.info("=" * 60)

    # ---- Configuration ----
    try:
        config = ConfigLoader.load(args.config)
        logger.info("Configuration loaded: %s", config)
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Override log level from config if not debug CLI flag
    if not args.debug:
        config_level = config.get("system", "log_level", default="INFO")
        setup_logging(config_level)

    # ---- Application ----
    app = BrailceApp(config)

    try:
        app.setup()
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        print(f"FATAL ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        app.shutdown()

    logger.info("Brailce terminated normally.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
