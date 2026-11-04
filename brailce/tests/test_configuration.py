"""
Brailce Phase 1 Tests – Configuration
=========================================

Tests for the configuration loader and defaults.
"""

import json
import os
import tempfile

import pytest

from brailce.config.defaults import DEFAULT_CONFIG
from brailce.config.loader import ConfigError, ConfigLoader


class TestDefaultConfig:
    """Tests for default configuration values."""

    def test_default_simulation_mode_is_true(self) -> None:
        assert DEFAULT_CONFIG["system"]["simulation_mode"] is True

    def test_default_input_device_is_keyboard(self) -> None:
        assert DEFAULT_CONFIG["input"]["device"] == "keyboard"

    def test_default_speech_enabled(self) -> None:
        assert DEFAULT_CONFIG["speech"]["enabled"] is True

    def test_default_ai_enabled(self) -> None:
        assert DEFAULT_CONFIG["ai"]["enabled"] is True

    def test_default_display_driver_is_console(self) -> None:
        assert DEFAULT_CONFIG["display"]["driver"] == "console"

    def test_all_sections_present(self) -> None:
        required = ["system", "input", "braille", "speech", "display",
                     "ai", "logging", "power"]
        for section in required:
            assert section in DEFAULT_CONFIG, f"Missing section: {section}"


class TestConfigLoader:
    """Tests for ConfigLoader."""

    def test_from_defaults(self) -> None:
        config = ConfigLoader.from_defaults()
        assert config.simulation_mode is True
        assert config.input_device == "keyboard"

    def test_load_nonexistent_file_uses_defaults(self) -> None:
        config = ConfigLoader.load("nonexistent_file_xyz.json")
        assert config.simulation_mode is True

    def test_load_valid_json(self) -> None:
        data = {"system": {"simulation_mode": False}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            tmp_path = f.name

        try:
            config = ConfigLoader.load(tmp_path)
            assert config.simulation_mode is False
            # Other defaults should remain
            assert config.input_device == "keyboard"
        finally:
            os.unlink(tmp_path)

    def test_load_malformed_json_raises_error(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{invalid json!!!}")
            tmp_path = f.name

        try:
            with pytest.raises(ConfigError, match="Malformed JSON"):
                ConfigLoader.load(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_get_nested_value(self) -> None:
        config = ConfigLoader.from_defaults()
        host = config.get("ai", "host")
        assert host == "http://127.0.0.1:11434"

    def test_get_missing_key_returns_default(self) -> None:
        config = ConfigLoader.from_defaults()
        val = config.get("nonexistent", "key", default="fallback")
        assert val == "fallback"

    def test_section_returns_copy(self) -> None:
        config = ConfigLoader.from_defaults()
        speech = config.section("speech")
        assert isinstance(speech, dict)
        assert speech["enabled"] is True
        # Modifying the returned dict should not affect config
        speech["enabled"] = False
        assert config.get("speech", "enabled") is True

    def test_deep_merge_preserves_defaults(self) -> None:
        data = {"speech": {"volume": 70}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            tmp_path = f.name

        try:
            config = ConfigLoader.load(tmp_path)
            assert config.get("speech", "volume") == 70
            # Other speech defaults should remain
            assert config.get("speech", "enabled") is True
            assert config.get("speech", "model_path") == "~/piper/en_US-ryan-medium.onnx"
        finally:
            os.unlink(tmp_path)
