"""Regression coverage for the unified Piper speech pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from brailce.config.loader import ConfigLoader
from brailce.core.app import BrailceApp
from brailce.input.keyboard_input import SUPPORTED_CHARACTERS
from brailce.modes.free_input import FreeInputMode
from brailce.speech.normalizer import normalize_for_piper
from brailce.speech.piper_engine import PiperEngine, _cache_fingerprint
from brailce.speech.pronunciation import (
    CHARACTER_PRONUNCIATIONS,
    pronunciation_for,
)
from brailce.speech.service import SpeechService


class RecordingEngine:
    engine_name = "Piper (test)"

    def __init__(self) -> None:
        self.spoken_items: list[str] = []
        self.model_path = ""
        self.settings = {}
        self.stopped = False

    def speak(self, text: str, interrupt=None) -> None:
        self.spoken_items.append(text)

    def stop(self) -> None:
        self.stopped = True

    def is_available(self) -> bool:
        return True

    def set_voice(self, voice: str) -> None:
        self.model_path = voice

    def set_rate(self, rate: int) -> None:
        pass

    def set_volume(self, volume: int) -> None:
        pass


def test_pronunciation_table_covers_every_supported_character() -> None:
    assert SUPPORTED_CHARACTERS <= set(CHARACTER_PRONUNCIATIONS)
    for character in SUPPORTED_CHARACTERS:
        spoken = CHARACTER_PRONUNCIATIONS[character]
        assert spoken.strip()
        assert spoken.strip().rstrip(".").lower() != character.lower()


def test_requested_letter_names_have_explicit_pronunciations() -> None:
    assert [pronunciation_for(letter) for letter in "AIZUW"] == [
        "ay.", "eye.", "zee.", "you.", "double you."
    ]


def test_single_engine_uses_one_model_and_settings_for_all_speech_paths() -> None:
    engine = RecordingEngine()
    created_settings = {}

    def create_engine(**settings):
        created_settings.update(settings)
        engine.model_path = settings["model_path"]
        engine.settings = {
            key: value
            for key, value in settings.items()
            if key != "model_path" and key != "max_queue_size" and key != "speaker_id"
        }
        return engine

    with patch("brailce.speech.service.PiperEngine", side_effect=create_engine):
        service = SpeechService.from_config(ConfigLoader.from_defaults())

    assert service.character_engine is service.text_engine is service.piper_engine is engine
    service.speak_text("Free Input Mode. Ready to type.")
    service.speak_character("A")
    service.speak_word("CAT")
    service.speak_text("Hello, world!")
    assert engine.spoken_items == [
        "Free Input Mode. Ready to type.",
        "ay.",
        "cat.",
        "Hello, world!",
    ]
    assert Path(engine.model_path).name == "en_US-ryan-medium.onnx"
    assert created_settings["length_scale"] == 1.08
    assert created_settings["noise_scale"] == 0.5
    assert created_settings["noise_w"] == 0.6
    assert created_settings["sentence_silence"] == 0.2
    assert created_settings["volume"] == 100
    assert engine.settings["length_scale"] == 1.08


def test_space_speaks_words_and_spells_non_words_through_same_service() -> None:
    engine = RecordingEngine()
    speech = SpeechService(piper_engine=engine)
    app = BrailceApp(ConfigLoader.from_defaults())
    app.speech = speech
    app.display = None
    app.state.text_buffer = "CAT"
    app.state.number_mode = False
    FreeInputMode(app)._handle_space()
    assert engine.spoken_items == ["cat."]

    engine.spoken_items.clear()
    app.state.text_buffer = "XQZ"
    FreeInputMode(app)._handle_space()
    assert engine.spoken_items == ["ex.", "cue.", "zee."]

    engine.spoken_items.clear()
    app.state.text_buffer = "A1B"
    FreeInputMode(app)._handle_space()
    assert engine.spoken_items == ["ay.", "one.", "bee."]


def test_number_tokens_and_compact_math_are_normalized() -> None:
    speech = SpeechService(piper_engine=RecordingEngine())
    assert speech._digit_token_mode == "number"
    assert normalize_for_piper("2+3") == "two plus three."
    assert normalize_for_piper("HELLO, WORLD!") == "Hello, world!"


def test_pronunciation_cache_fingerprint_changes_with_synthesis_settings(tmp_path) -> None:
    model = tmp_path / "voice.onnx"
    model_config = tmp_path / "voice.onnx.json"
    model.write_bytes(b"model")
    model_config.write_text('{"audio":{"sample_rate":22050}}', encoding="utf-8")
    settings = {
        "length_scale": 1.08,
        "noise_scale": 0.5,
        "noise_w": 0.6,
        "sentence_silence": 0.2,
        "leading_silence_ms": 100,
        "trailing_silence_ms": 150,
        "volume": 100,
    }
    original = _cache_fingerprint(
        str(model), str(model_config), settings, speaker_id=None
    )
    changed_settings = dict(settings, length_scale=1.2)
    changed = _cache_fingerprint(
        str(model), str(model_config), changed_settings, speaker_id=None
    )
    assert original != changed


def test_piper_cache_directory_changes_when_settings_change(tmp_path) -> None:
    model = tmp_path / "voice.onnx"
    model_config = tmp_path / "voice.onnx.json"
    binary = tmp_path / "piper"
    model.write_bytes(b"model")
    model_config.write_text('{"audio":{"sample_rate":22050}}', encoding="utf-8")
    binary.write_bytes(b"test executable")
    with patch.object(PiperEngine, "_start_cache_generation"):
        engine = PiperEngine(
            binary_path=str(binary),
            model_path=str(model),
            cache_root=str(tmp_path / "cache"),
        )
        original_cache = engine._cache_dir
        engine.set_volume(75)
    assert engine._cache_dir != original_cache
