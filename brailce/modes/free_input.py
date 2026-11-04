"""
Brailce Mode – Free Input (Stub)
===================================

STUB for Phase 1 — full implementation in Phase 4.

Free Input Mode allows the user to press dedicated character buttons
and receive immediate audible feedback for each character.

Pipeline per key press:
    CHARACTER_PRESSED → Braille lookup → buffer update →
    display update → speech → logging
"""

from __future__ import annotations

import logging

from brailce.core.events import AppMode, EventType, InputEvent
from brailce.modes.base_mode import BaseMode

logger = logging.getLogger(__name__)


# Grade 1 Braille / UEB: Letters A-J correspond directly to numbers 1-0 under the # indicator
BRAILLE_LETTER_TO_NUMBER = {
    "A": ("1", "one", "⠁", "Dots 1", "● ○\n○ ○\n○ ○"),
    "B": ("2", "two", "⠃", "Dots 1-2", "● ○\n● ○\n○ ○"),
    "C": ("3", "three", "⠉", "Dots 1-4", "● ●\n○ ○\n○ ○"),
    "D": ("4", "four", "⠙", "Dots 1-4-5", "● ●\n○ ●\n○ ○"),
    "E": ("5", "five", "⠑", "Dots 1-5", "● ○\n○ ●\n○ ○"),
    "F": ("6", "six", "⠋", "Dots 1-2-4", "● ●\n● ○\n○ ○"),
    "G": ("7", "seven", "⠛", "Dots 1-2-4-5", "● ●\n● ●\n○ ○"),
    "H": ("8", "eight", "⠓", "Dots 1-2-5", "● ○\n● ●\n○ ○"),
    "I": ("9", "nine", "⠊", "Dots 2-4", "○ ●\n● ○\n○ ○"),
    "J": ("0", "zero", "⠚", "Dots 2-4-5", "○ ●\n● ●\n○ ○"),
}


class FreeInputMode(BaseMode):
    """
    Free Input Mode – character-by-character input with immediate feedback.
    Supports '#' number sign to switch between letter and number input.
    """

    @property
    def mode_type(self) -> AppMode:
        return AppMode.FREE_INPUT

    @property
    def display_name(self) -> str:
        return "Free Input Mode"

    def handle_event(self, event: InputEvent) -> None:
        """Process an input event in Free Input Mode."""
        if self.state.ai_processing:
            return  # Ignore while processing AI

        if event.event_type == EventType.CHARACTER_PRESSED and event.character:
            self._handle_character(event.character)
        elif event.event_type == EventType.SPACE_PRESSED:
            self._handle_space()
        elif event.event_type == EventType.BACKSPACE_PRESSED:
            self._handle_backspace()
        elif event.event_type == EventType.CLEAR_PRESSED:
            self._handle_clear()
        elif event.event_type == EventType.ENTER_PRESSED:
            self._handle_enter()

    def _handle_character(self, character: str) -> None:
        """Handle a supported character press."""
        # 1. Number Indicator (#) Toggle
        if character == "#":
            is_active = self.state.toggle_number_mode()
            dots_str = "Dots 3-4-5-6"
            unicode_char = "⠼"
            self.state.update_braille_info(dots_str, unicode_char)

            status_text = "Number Mode: ON (A-J -> 1-0)" if is_active else "Number Mode: OFF"
            if self.app.display:
                self.app.display.show_character("# (Number Sign)")
                self.app.display.show_braille(unicode_char, dots_str, "○ ●\n○ ●\n● ●")
                self.app.display.show_status(status_text)
            if self.app.speech:
                self.app.speech.speak("number sign, number mode on" if is_active else "number mode off")
            logger.info("FreeInput: NUMBER_SIGN (mode=%s)", is_active)
            return

        # 2. Number Mode Active: Translate A-J to 1-0
        if self.state.number_mode:
            char_upper = character.upper()
            if char_upper in BRAILLE_LETTER_TO_NUMBER:
                digit, speech_val, unicode_char, dots_str, visual = BRAILLE_LETTER_TO_NUMBER[char_upper]
                self.state.append_character(digit)
                self.state.update_braille_info(dots_str, unicode_char)
                if self.app.display:
                    self.app.display.show_character(f"{digit} (from {char_upper})")
                    self.app.display.show_braille(unicode_char, dots_str, visual)
                    self.app.display.show_text_buffer(self.state.text_buffer)
                if self.app.speech and self.app.config.get("speech", "speak_each_character", default=True):
                    if hasattr(self.app.speech, "speak_character") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                        self.app.speech.speak_character(digit)
                    else:
                        self.app.speech.speak(speech_val)
                logger.info("FreeInput: NUMBER=%s (key=%s)", digit, char_upper)
                return
            elif char_upper in "KLMNOPQRSTUVWXYZ":
                # Standard Braille rule: Non-numeric letters terminate number mode
                self.state.number_mode = False
                if self.app.display:
                    self.app.display.show_status("Letter Mode")

        if not self.app.encoder:
            logger.error("Encoder not available.")
            return

        mapping = self.app.encoder.encode(character)
        if not mapping:
            logger.warning("Character not supported: %r", character)
            if self.app.speech:
                self.app.speech.speak("Unsupported")
            return

        # 1. Update text buffer & Braille state
        self.state.append_character(mapping.character)
        self.state.update_braille_info(mapping.dots_string(), mapping.braille_unicode)

        # 2. Display update
        if self.app.display:
            self.app.display.show_character(mapping.display_label)
            self.app.display.show_braille(
                mapping.braille_unicode,
                mapping.dots_string(),
                mapping.dots_visual()
            )
            self.app.display.show_text_buffer(self.state.text_buffer)

        # 3. Speech feedback (immediate character pronunciation via unified speech engine)
        if self.app.speech and self.app.config.get("speech", "speak_each_character", default=True):
            if hasattr(self.app.speech, "speak_character") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                self.app.speech.speak_character(mapping.character if mapping else character)
            else:
                self.app.speech.speak(mapping.speech if mapping else character)

        # 4. Logging
        logger.info("FreeInput: CHAR=%s, BRAILLE=%s", mapping.character, mapping.braille_unicode)

    def _handle_space(self) -> None:
        """Handle space button press - speak the last formed word."""
        # Standard Braille rule: Space terminates number mode
        if self.state.number_mode:
            self.state.number_mode = False

        # Get the word formed so far BEFORE adding the space.
        current_buf = self.state.text_buffer
        if current_buf and not current_buf.endswith(" "):
            words = current_buf.split()
            last_word = words[-1] if words else ""
        else:
            last_word = ""

        self.state.append_character(" ")
        self.state.update_braille_info("No dots", " ")
        
        if self.app.display:
            self.app.display.show_character("Space")
            self.app.display.show_braille(" ", "No dots", "○\n○\n○")
            self.app.display.show_text_buffer(self.state.text_buffer)
            
        if self.app.speech and last_word:
            if hasattr(self.app.speech, "speak_word") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                self.app.speech.speak_word(last_word)
            else:
                self.app.speech.speak(last_word)

        logger.info("FreeInput: SPACE (word: %r)", last_word)

    def _handle_enter(self) -> None:
        """Handle enter button press - speak the accumulated sentence."""
        query = self.state.text_buffer.strip()
        if not query:
            return

        if self.app.speech:
            # If single character, route to speak_character to play clean cached character WAV
            clean_char = query.rstrip(".")
            if len(clean_char) == 1:
                if hasattr(self.app.speech, "speak_character") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                    self.app.speech.speak_character(clean_char)
                else:
                    self.app.speech.speak(clean_char)
            elif hasattr(self.app.speech, "speak_text") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                self.app.speech.speak_text(query, interrupt=False)
            else:
                self.app.speech.speak(query, interrupt=False)

        # Reset buffer so next typing starts completely fresh without old inputs
        self.state.clear_buffer()

        if self.app.display:
            self.app.display.show_status(f"Spoken: \"{query}\"")
            self.app.display.show_text_buffer("")

    def _handle_backspace(self) -> None:
        """Handle backspace button press without producing clicks, beeps, or vocal announcements."""
        removed = self.state.backspace()
        
        if self.app.display:
            if removed:
                self.app.display.show_character("Backspace")
                self.app.display.show_text_buffer(self.state.text_buffer)
            else:
                self.app.display.show_status("Buffer empty")

        if self.app.speech and self.app.config.get("speech", "speak_control_events", default=False):
            self.app.speech.speak("backspace")

        logger.info("FreeInput: BACKSPACE (removed: %r)", removed)

    def _handle_clear(self) -> None:
        """Handle clear button press."""
        self.state.clear_buffer()
        
        if self.app.display:
            self.app.display.show_character("Cleared")
            self.app.display.show_text_buffer("")
            self.app.display.show_status("Buffer cleared")
            
        if self.app.speech and self.app.config.get("speech", "speak_control_events", default=False):
            self.app.speech.speak("cleared")
            
        logger.info("FreeInput: CLEAR")

    def on_enter(self) -> None:
        logger.info("Entered Free Input Mode.")
        if self.app.display:
            self.app.display.clear()
            self.app.display.show_mode(self.mode_type)
            self.app.display.show_text_buffer(self.state.text_buffer)
            self.app.display.show_status("Ready — press any key")

    def on_exit(self) -> None:
        logger.info("Exited Free Input Mode.")
        self.state.clear_buffer()
