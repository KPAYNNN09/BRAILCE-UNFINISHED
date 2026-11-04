"""
Brailce Configuration Loader
===============================

Loads, validates, and provides access to application configuration.

Merge order:
    1. Built-in defaults (config/defaults.py)
    2. User-supplied config.json (merged on top)
    3. Runtime overrides (optional)

Usage:
    config = ConfigLoader.load("config/config.json")
    host = config.get("ai", "host")
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from brailce.config.defaults import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""


class ConfigLoader:
    """
    Loads configuration from JSON and merges with defaults.

    Attributes:
        _data: The fully merged configuration dictionary.
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        self._data: Dict[str, Any] = data or copy.deepcopy(DEFAULT_CONFIG)

    # ---- Factory Methods ----

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "ConfigLoader":
        """
        Load configuration from a JSON file, merged over defaults.

        Args:
            config_path: Path to config.json. If None, only defaults are used.

        Returns:
            A fully initialized ConfigLoader.

        Raises:
            ConfigError: If the JSON file is malformed.
        """
        merged = copy.deepcopy(DEFAULT_CONFIG)

        if config_path is not None:
            path = Path(config_path)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        user_config = json.load(f)
                    cls._deep_merge(merged, user_config)
                    logger.info("Configuration loaded from %s", path)
                except json.JSONDecodeError as exc:
                    raise ConfigError(
                        f"Malformed JSON in {path}: {exc}"
                    ) from exc
                except OSError as exc:
                    raise ConfigError(
                        f"Cannot read {path}: {exc}"
                    ) from exc
            else:
                logger.warning(
                    "Config file not found: %s — using defaults.", path
                )

        return cls(merged)

    @classmethod
    def from_defaults(cls) -> "ConfigLoader":
        """Create a ConfigLoader using only built-in defaults."""
        return cls(copy.deepcopy(DEFAULT_CONFIG))

    # ---- Access Methods ----

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Retrieve a nested configuration value.

        Args:
            *keys: Path of keys, e.g. get("ai", "host").
            default: Value to return if any key is missing.

        Returns:
            The configuration value, or *default* if not found.
        """
        node: Any = self._data
        for key in keys:
            if isinstance(node, dict):
                node = node.get(key)
                if node is None:
                    return default
            else:
                return default
        return node

    def section(self, name: str) -> Dict[str, Any]:
        """Return an entire configuration section as a dictionary."""
        sec = self._data.get(name, {})
        if not isinstance(sec, dict):
            return {}
        return copy.deepcopy(sec)

    @property
    def raw(self) -> Dict[str, Any]:
        """Return the full configuration dictionary (deep copy)."""
        return copy.deepcopy(self._data)

    # ---- Convenience Properties ----

    @property
    def simulation_mode(self) -> bool:
        return bool(self.get("system", "simulation_mode", default=True))

    @property
    def input_device(self) -> str:
        return str(self.get("input", "device", default="keyboard"))

    @property
    def speech_enabled(self) -> bool:
        return bool(self.get("speech", "enabled", default=True))

    @property
    def ai_enabled(self) -> bool:
        return bool(self.get("ai", "enabled", default=True))

    @property
    def display_driver(self) -> str:
        return str(self.get("display", "driver", default="console"))

    # ---- Internal ----

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """
        Recursively merge *override* into *base* in place.

        Nested dictionaries are merged; other values are overwritten.
        """
        for key, value in override.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                ConfigLoader._deep_merge(base[key], value)
            else:
                base[key] = value

    def __repr__(self) -> str:
        return f"ConfigLoader(sections={list(self._data.keys())})"
