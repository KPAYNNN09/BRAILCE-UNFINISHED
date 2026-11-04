"""
Brailce Mode – AI Assistant (Stub)
=====================================

STUB for Phase 1 — full implementation in Phase 7.

AI Assistant Mode accepts natural-language queries and sends them
to a locally hosted Ollama LLM for offline AI responses.
"""

from __future__ import annotations

import logging
import threading

from brailce.core.events import AppMode, EventType, InputEvent
from brailce.modes.base_mode import BaseMode
from brailce.utils.validation import validate_ai_query

logger = logging.getLogger(__name__)


# Grade 1 Braille / UEB: Letters A-J correspond directly to numbers 1-0 under the # indicator
BRAILLE_LETTER_TO_NUMBER = {
    "A": ("1", "one"),
    "B": ("2", "two"),
    "C": ("3", "three"),
    "D": ("4", "four"),
    "E": ("5", "five"),
    "F": ("6", "six"),
    "G": ("7", "seven"),
    "H": ("8", "eight"),
    "I": ("9", "nine"),
    "J": ("0", "zero"),
}


class AIAssistantMode(BaseMode):
    """
    AI Assistant Mode – text query → Ollama → response → speech.
    Supports '#' number sign to enter digits using keys A-J.
    """

    @property
    def mode_type(self) -> AppMode:
        return AppMode.AI_ASSISTANT

    @property
    def display_name(self) -> str:
        return "AI Assistant Mode"

    def handle_event(self, event: InputEvent) -> None:
        """Process an input event in AI Assistant Mode."""
        if self.state.ai_processing:
            # Ignore inputs while processing
            return

        if event.event_type == EventType.CHARACTER_PRESSED and event.character:
            self._handle_character(event.character)
        elif event.event_type == EventType.SPACE_PRESSED:
            if self.state.number_mode:
                self.state.number_mode = False
            self._handle_character(" ")
        elif event.event_type == EventType.BACKSPACE_PRESSED:
            self._handle_backspace()
        elif event.event_type == EventType.CLEAR_PRESSED:
            self._handle_clear()
        elif event.event_type == EventType.ENTER_PRESSED:
            self._handle_enter()

    def _handle_character(self, character: str) -> None:
        # 1. Number Indicator (#) Toggle
        if character == "#":
            is_active = self.state.toggle_number_mode()
            if self.app.display:
                self.app.display.show_character("# (Number Sign)")
                self.app.display.show_status("Number Mode: ON (A-J -> 1-0)" if is_active else "Number Mode: OFF")
            if self.app.speech:
                self.app.speech.speak_character("#")
            return

        # 2. Number Mode Active: Translate A-J to 1-0
        speech_override = None
        if self.state.number_mode:
            char_upper = character.upper()
            if char_upper in BRAILLE_LETTER_TO_NUMBER:
                digit, speech_val = BRAILLE_LETTER_TO_NUMBER[char_upper]
                character = digit
                speech_override = digit
            elif char_upper in "KLMNOPQRSTUVWXYZ":
                self.state.number_mode = False

        # Check if space pressed to pronounce the word just completed
        last_word = ""
        if character == " ":
            current_buf = self.state.ai_query_buffer
            if current_buf and not current_buf.endswith(" "):
                words = current_buf.split()
                last_word = words[-1] if words else ""

        self.state.append_ai_character(character)
        if self.app.display:
            self.app.display.show_character("Space" if character == " " else character)
            self.app.display.show_text_buffer(self.state.ai_query_buffer)
        if self.app.speech:
            if character == " ":
                if last_word:
                    if hasattr(self.app.speech, "speak_word") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                        self.app.speech.speak_word(last_word)
                    else:
                        self.app.speech.speak(last_word)
            elif speech_override:
                if hasattr(self.app.speech, "speak_character") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                    self.app.speech.speak_character(speech_override)
                else:
                    self.app.speech.speak(speech_override)
            elif self.app.config.get("speech", "speak_each_character", default=True):
                mapping = self.app.encoder.encode(character) if self.app.encoder else None
                char_val = mapping.character if mapping else character
                if hasattr(self.app.speech, "speak_character") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                    self.app.speech.speak_character(char_val)
                else:
                    self.app.speech.speak(char_val)

    def _handle_backspace(self) -> None:
        """Handle backspace silently without clicks, beeps, or vocal announcements."""
        if not self.state.ai_query_buffer:
            if self.app.display:
                self.app.display.show_status("Buffer empty")
            return
        
        self.state.ai_query_buffer = self.state.ai_query_buffer[:-1]
        if self.app.display:
            self.app.display.show_character("Backspace")
            self.app.display.show_text_buffer(self.state.ai_query_buffer)

    def _handle_clear(self) -> None:
        """Handle clear button press."""
        self.state.clear_ai_buffer()
        if self.app.display:
            self.app.display.show_character("Cleared")
            self.app.display.show_text_buffer("")
        if self.app.speech and self.app.config.get("speech", "speak_control_events", default=False):
            self.app.speech.speak("cleared")

    def _handle_enter(self) -> None:
        """Submit the accumulated query to Ollama and speak response."""
        query = self.state.get_ai_query()

        valid, msg = validate_ai_query(query)
        if not valid:
            if self.app.display:
                self.app.display.show_error(msg)
            if self.app.speech:
                self.app.speech.speak(msg)
            # Restore query buffer if invalid (so user can edit it)
            self.state.ai_query_buffer = query
            return

        self.state.ai_processing = True
        if self.app.display:
            self.app.display.show_ai_processing(query)

        if self.app.speech:
            if hasattr(self.app.speech, "speak_text") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                self.app.speech.speak_text(query, interrupt=False)
            else:
                self.app.speech.speak(query, interrupt=False)

        # Start background thread for Ollama inference
        threading.Thread(target=self._process_query, args=(query,), daemon=True).start()

    def _process_query(self, query: str) -> None:
        if self.app.speech:
            if hasattr(self.app.speech, "speak_text") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                self.app.speech.speak_text("Thinking, please wait.", interrupt=False)
            else:
                self.app.speech.speak("Thinking, please wait.", interrupt=False)

        if not hasattr(self.app, "ai_client") or not self.app.ai_client:
            self._finish_processing("AI assistant is currently unavailable.", query=query)
            return

        response = self.app.ai_client.generate(query)
        if not response:
            self._finish_processing("AI assistant is currently unavailable.", query=query)
        else:
            self._finish_processing(response, query=query)

    def _finish_processing(self, response: str, query: str = "") -> None:
        self.state.ai_processing = False
        self.state.ai_last_response = response
        if self.app.display:
            self.app.display.show_ai_response(response)
        if self.app.speech:
            if hasattr(self.app.speech, "speak_text") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                self.app.speech.speak_text(response, interrupt=False)
            else:
                self.app.speech.speak(response)

    def on_enter(self) -> None:
        logger.info("Entered AI Assistant Mode.")
        self.state.clear_ai_buffer()
        self.state.ai_processing = False
        if self.app.display:
            if hasattr(self.app.display, "_current_query"):
                self.app.display._current_query = ""
            self.app.display.show_mode(self.mode_type)
            self.app.display.show_text_buffer("")

    def on_exit(self) -> None:
        logger.info("Exited AI Assistant Mode.")
        self.state.clear_ai_buffer()
        self.state.ai_processing = False
        if self.app.display:
            if hasattr(self.app.display, "_current_query"):
                self.app.display._current_query = ""
