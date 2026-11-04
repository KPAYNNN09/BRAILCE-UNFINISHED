"""Single-engine speech service used by every Brailce mode."""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, Optional, Tuple

from brailce.config.defaults import DEFAULT_CONFIG
from brailce.speech.base import SpeechEngine
from brailce.speech.normalizer import (
    DIGIT_MAP,
    LETTER_MAP,
    LETTER_NAME_MAP,
    MATH_OPERATORS,
    PUNCTUATION_MAP,
    normalize_for_piper,
)
from brailce.speech.piper_engine import PiperEngine
from brailce.speech.pronunciation import (
    CHARACTER_PRONUNCIATIONS,
    is_word_token,
    pronunciation_for,
    spelled_pronunciations,
)

logger = logging.getLogger(__name__)

DIGIT_NAME_MAP: Dict[str, str] = dict(DIGIT_MAP)
MATH_SYMBOL_MAP: Dict[str, str] = dict(MATH_OPERATORS)
PUNCTUATION_NAME_MAP: Dict[str, str] = dict(PUNCTUATION_MAP)
VALID_BEHAVIORS = {"character", "character_and_word", "completed_text_only"}


class SpeechService(SpeechEngine):
    """Normalizes all spoken content and routes it through one Piper engine."""

    def __init__(
        self,
        character_engine: Optional[SpeechEngine] = None,
        text_engine: Optional[SpeechEngine] = None,
        piper_engine: Optional[SpeechEngine] = None,
        behavior: str = "character_and_word",
        voice: Optional[str] = None,
        rate: Optional[int] = None,
        volume: Optional[int] = None,
        pitch: Optional[int] = None,
        digit_token_mode: str = "number",
    ) -> None:
        self._engine = piper_engine or text_engine or character_engine or PiperEngine(
            model_path=voice,
            volume=volume,
        )
        self._behavior = behavior if behavior in VALID_BEHAVIORS else "character_and_word"
        self._voice = voice
        self._rate = rate
        self._volume = volume
        self._pitch = pitch
        self._digit_token_mode = digit_token_mode
        self._last_utterance: Optional[Tuple[str, str, Dict[str, Any]]] = None
        self._lock = threading.Lock()

    @property
    def engine_name(self) -> str:
        return f"SpeechService ({self._engine.engine_name})"

    @property
    def character_engine(self) -> SpeechEngine:
        return self._engine

    @property
    def text_engine(self) -> SpeechEngine:
        return self._engine

    @property
    def piper_engine(self) -> SpeechEngine:
        return self._engine

    def wait_until_idle(self, timeout: Optional[float] = None) -> bool:
        wait = getattr(self._engine, "wait_until_idle", None)
        return bool(wait(timeout)) if callable(wait) else True

    @property
    def behavior(self) -> str:
        return self._behavior

    @property
    def last_utterance(self) -> Optional[str]:
        return self._last_utterance[1] if self._last_utterance else None

    def set_behavior(self, behavior: str) -> None:
        if behavior in VALID_BEHAVIORS:
            self._behavior = behavior

    def is_available(self) -> bool:
        return self._engine.is_available()

    def set_voice(self, voice: str) -> None:
        self._voice = voice
        self._engine.set_voice(voice)

    def set_rate(self, rate: int) -> None:
        self._rate = rate
        self._engine.set_rate(rate)

    def set_volume(self, volume: int) -> None:
        self._volume = volume
        self._engine.set_volume(volume)

    def set_pitch(self, pitch: int) -> None:
        self._pitch = pitch

    def stop_speech(self) -> None:
        self.stop()

    def stop_current(self) -> None:
        self.stop()

    def stop(self) -> None:
        self._engine.stop()

    def shutdown(self) -> None:
        self.stop()

    def speak_character(self, character: str) -> None:
        if not character or self._behavior == "completed_text_only":
            return
        character = character[0]
        normalized = pronunciation_for(character)
        if not normalized:
            logger.warning("Unsupported speech character: %r", character)
            return
        self._record_utterance("character", normalized, {"character": character})
        with self._lock:
            cached_speaker = getattr(self._engine, "speak_character", None)
            if callable(cached_speaker):
                cached_speaker(character, normalized)
            else:
                self._engine.speak(normalized)

    def speak_word(self, word: str) -> None:
        token = word.strip()
        if not token:
            return
        if len(token) == 1 and token in CHARACTER_PRONUNCIATIONS:
            self.speak_character(token)
            return
        if token.isdigit():
            if self._digit_token_mode == "digits":
                self._speak_spelled_token(token, "word")
            else:
                self._speak_text(token, "word", is_word=True)
            return
        word_core = token.strip(".,!?")
        if is_word_token(word_core):
            self._speak_text(token, "word", is_word=True)
            return
        if any(symbol in token for symbol in "+-*/×÷=") and any(
            character.isdigit() for character in token
        ):
            self.speak_text(token)
            return
        self._speak_spelled_token(token, "word")

    def _speak_spelled_token(self, token: str, kind: str) -> None:
        pronunciations = spelled_pronunciations(token)
        for pronunciation in pronunciations:
            self._queue_pronunciation(pronunciation)
        if pronunciations:
            self._record_utterance(kind, " ".join(pronunciations), {"word": token})

    def speak_symbol(self, symbol: str, context: str = "text") -> None:
        del context
        self.speak_character(symbol)

    def speak_text(
        self,
        text: str,
        interrupt: bool = False,
        engine_hint: Optional[str] = None,
    ) -> None:
        del engine_hint
        if not text:
            return
        clean = text.strip()
        if len(clean) == 1:
            self.speak_character(clean)
            return
        if len(clean.split()) == 1 and not any(
            character in "+-*/=" for character in clean
        ):
            self.speak_word(clean)
            return
        self._speak_text(clean, "text", interrupt=interrupt)

    def _speak_text(
        self,
        text: str,
        kind: str,
        is_word: bool = False,
        interrupt: bool = False,
    ) -> None:
        normalized = normalize_for_piper(text, is_word=is_word)
        if not normalized:
            return
        self._record_utterance(kind, normalized, {"interrupt": interrupt})
        with self._lock:
            self._engine.speak(normalized, interrupt=interrupt)

    def _queue_pronunciation(self, spoken_text: str) -> None:
        with self._lock:
            self._engine.speak(spoken_text)

    def speak_math_expression(self, expression: str) -> None:
        if expression:
            self.speak_text(expression)

    def replay_last_utterance(self) -> None:
        if not self._last_utterance:
            return
        kind, text, kwargs = self._last_utterance
        if kind == "character":
            self.speak_character(kwargs["character"])
        elif kind == "word":
            self.speak_word(kwargs["word"])
        else:
            self.speak_text(text, interrupt=True)

    def speak(self, text: str, interrupt: Optional[bool] = None) -> None:
        """Compatibility entry point; all speech still follows the Piper path."""
        self.speak_text(text, interrupt=bool(interrupt))

    def _record_utterance(self, kind: str, text: str, kwargs: Dict[str, Any]) -> None:
        self._last_utterance = (kind, text, kwargs)

    @classmethod
    def from_config(cls, config: Any) -> "SpeechService":
        default_speech_config = DEFAULT_CONFIG["speech"]
        speech_cfg = config.section("speech") if hasattr(config, "section") else {}
        setting = lambda name: speech_cfg.get(name, default_speech_config[name])
        engine_name = str(setting("engine")).lower()
        if engine_name != "piper":
            raise RuntimeError(
                f"Unsupported speech.engine={engine_name!r}; Brailce speech requires Piper."
            )

        model_path = os.path.expandvars(
            os.path.expanduser(
                str(setting("model_path"))
            )
        )
        piper = PiperEngine(
            model_path=model_path,
            length_scale=float(setting("length_scale")),
            noise_scale=float(setting("noise_scale")),
            noise_w=float(setting("noise_w")),
            sentence_silence=float(setting("sentence_silence")),
            leading_silence_ms=int(setting("leading_silence_ms")),
            trailing_silence_ms=int(setting("trailing_silence_ms")),
            volume=int(setting("volume")),
            speaker_id=setting("speaker_id"),
            max_queue_size=int(setting("max_queue_size")),
        )
        if not piper.is_available():
            raise RuntimeError(piper.availability_error())

        return cls(
            piper_engine=piper,
            behavior=str(setting("behavior")),
            voice=model_path,
            volume=int(setting("volume")),
            digit_token_mode=str(setting("digit_token_mode")),
        )
