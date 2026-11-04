"""Brailce – Speech engine module."""

from brailce.speech.base import SpeechEngine
from brailce.speech.normalizer import (
    is_keystroke_feedback,
    normalize_for_espeak_character,
    normalize_for_piper,
)
from brailce.speech.piper_engine import PiperEngine
from brailce.speech.service import SpeechService

__all__ = [
    "SpeechEngine",
    "PiperEngine",
    "SpeechService",
    "normalize_for_piper",
    "normalize_for_espeak_character",
    "is_keystroke_feedback",
]
