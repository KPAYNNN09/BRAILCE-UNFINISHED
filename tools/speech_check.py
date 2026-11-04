"""Audition all configured Brailce pronunciations through the production pipeline."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brailce.config.loader import ConfigLoader
from brailce.speech.pronunciation import CHARACTER_PRONUNCIATIONS
from brailce.speech.service import SpeechService


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    config = ConfigLoader.load(str(PROJECT_ROOT / "brailce" / "config" / "config.json"))
    speech_config = config.section("speech")
    configured_model = os.path.expandvars(
        os.path.expanduser(
            str(speech_config.get("model_path", "~/piper/en_US-ryan-medium.onnx"))
        )
    )
    configured_settings = {
        key: speech_config.get(key)
        for key in (
            "length_scale",
            "noise_scale",
            "noise_w",
            "sentence_silence",
            "leading_silence_ms",
            "trailing_silence_ms",
            "volume",
            "speaker_id",
        )
    }
    print(f"Configured model: {configured_model}")
    print(f"Configured model config: {configured_model}.json")
    print(f"Configured settings: {json.dumps(configured_settings, sort_keys=True)}")
    try:
        speech = SpeechService.from_config(config)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    engine = speech.piper_engine
    print(f"Model: {engine.model_path}")
    print(f"Model config: {engine.model_config_path}")
    print(f"Speaker ID: {engine.speaker_id if engine.speaker_id is not None else 'model default'}")
    print(f"Sample rate: {engine.sample_rate or 'read from Piper output'} Hz")
    print(f"Settings: {json.dumps(engine.settings, sort_keys=True)}")

    print("Speaking supported characters...")
    for character in CHARACTER_PRONUNCIATIONS:
        speech.speak_character(character)
    speech.wait_until_idle()

    print("Speaking words and tokens...")
    for word in ("CAT", "HELLO", "XQZ", "A1B", "123"):
        speech.speak_word(word)
    speech.wait_until_idle()

    print("Speaking sentences and math...")
    for sentence in (
        "HELLO, WORLD!",
        "Piper speech should sound consistent across every mode.",
        "2+3",
    ):
        speech.speak_text(sentence)
    speech.wait_until_idle()

    print("Speaking mode introductions...")
    for introduction in (
        "Free Input Mode.",
        "Math Mode.",
        "AI Assistant Mode.",
        "Scanner Mode.",
    ):
        speech.speak_text(introduction)
    speech.wait_until_idle()
    speech.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
