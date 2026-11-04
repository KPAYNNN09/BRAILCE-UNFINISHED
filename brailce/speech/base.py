"""
Brailce Speech Engine – Abstract Base
=======================================

Defines the interface for all speech engines.

The application calls speak(), stop(), etc. without knowledge
of the underlying TTS technology.

Concrete implementations:
    - PiperEngine     (Piper neural TTS — offline)
    - MockSpeechEngine (unit testing)
"""

from __future__ import annotations

import abc
from typing import Optional


class SpeechEngine(abc.ABC):
    """Abstract interface for text-to-speech engines."""

    @abc.abstractmethod
    def speak(self, text: str) -> None:
        """
        Enqueue text for immediate speech output.

        For Free Input Mode, each character press calls this method
        with the single character or its speech representation.
        """

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop any currently playing speech."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check whether the TTS engine is available on this system."""

    @abc.abstractmethod
    def set_voice(self, voice: str) -> None:
        """Set the TTS voice/language."""

    @abc.abstractmethod
    def set_rate(self, rate: int) -> None:
        """Set the speech rate (words per minute)."""

    @abc.abstractmethod
    def set_volume(self, volume: int) -> None:
        """Set the speech volume (0–100)."""

    @property
    @abc.abstractmethod
    def engine_name(self) -> str:
        """Human-readable name for this speech engine."""
