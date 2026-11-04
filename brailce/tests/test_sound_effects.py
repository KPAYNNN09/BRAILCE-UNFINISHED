"""
Brailce Unit Tests – Sound Effects Engine
==========================================

Tests the acoustic earcons and sound synthesis engine.
"""

import os
import wave
import pytest

from brailce.audio.sound_effects import SoundEffectsEngine


class TestSoundEffectsEngine:
    @pytest.fixture
    def sound_engine(self) -> SoundEffectsEngine:
        return SoundEffectsEngine(enabled=True, volume=80)

    def test_engine_initialization(self, sound_engine: SoundEffectsEngine) -> None:
        assert sound_engine.enabled is True
        assert sound_engine.volume == 80
        assert sound_engine.is_available() is True

    def test_all_expected_earcons_generated(self, sound_engine: SoundEffectsEngine) -> None:
        expected_sounds = [
            "key_press",
            "space",
            "backspace",
            "boundary",
            "clear",
            "number_on",
            "number_off",
            "mode_switch",
            "enter",
            "success",
            "error",
            "thinking",
            "camera_shutter",
        ]
        for name in expected_sounds:
            assert name in sound_engine._sound_files, f"Sound {name} missing from engine"
            path = sound_engine._sound_files[name]
            assert os.path.exists(path), f"File {path} not found on disk"
            assert os.path.getsize(path) > 100, f"File {path} unexpectedly small"
            
            # Verify valid WAV file header and parameters
            with wave.open(path, "rb") as w:
                assert w.getnchannels() == 1
                assert w.getsampwidth() == 2
                assert w.getframerate() == 22050
                assert w.getnframes() > 0

    def test_volume_clamping_and_setter(self, sound_engine: SoundEffectsEngine) -> None:
        sound_engine.set_volume(150)
        assert sound_engine.volume == 100

        sound_engine.set_volume(-20)
        assert sound_engine.volume == 0

        sound_engine.set_volume(75)
        assert sound_engine.volume == 75

    def test_play_valid_sounds_no_exception(self, sound_engine: SoundEffectsEngine) -> None:
        # Playing should execute without error
        sound_engine.play("key_press")
        sound_engine.play("number_on")
        sound_engine.play("number_off")
        sound_engine.play("mode_switch")
        sound_engine.play("non_existent_sound")  # Graceful ignore

    def test_volume_tick(self, sound_engine: SoundEffectsEngine) -> None:
        sound_engine.play_volume_tick(50)
        sound_engine.play_volume_tick(100)
        sound_engine.play_volume_tick(0)

    def test_disabled_engine_does_not_play(self) -> None:
        disabled = SoundEffectsEngine(enabled=False, volume=80)
        assert disabled.is_available() is False
        disabled.play("key_press")  # Should be a no-op
