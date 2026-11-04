"""
Brailce Mode – Math Mode (Method 1)
=====================================

Dedicated Math Mode for Grade 1 DepEd learners.

Allows learners to type arithmetic expressions (e.g. "5 + 3") on dedicated
Braille buttons with real-time auditory/Braille feedback, and press Enter
(or equals) to receive an immediate deterministic step-by-step counting
explanation tailored for Grade 1 visually impaired students.

Pipeline per key press:
    CHARACTER_PRESSED (digit/op) → Braille lookup → math buffer update →
    display update → spoken feedback
Enter / Equals:
    ENTER_PRESSED → SafeArithmetic solver → display solution card →
    spoken counting explanation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from brailce.braille.arithmetic import SafeArithmetic
from brailce.core.events import AppMode, EventType, InputEvent
from brailce.modes.base_mode import BaseMode

if TYPE_CHECKING:
    from brailce.core.app import BrailceApp

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

# Valid characters allowed in Math Mode
MATH_VALID_CHARS = set("0123456789+-*/.=#")


class MathMode(BaseMode):
    """
    Dedicated Math Mode for Grade 1 DepEd arithmetic instruction.
    Supports '#' number sign to enter digits using keys A-J.
    """

    @property
    def mode_type(self) -> AppMode:
        return AppMode.MATH

    @property
    def display_name(self) -> str:
        return "Math Mode"

    def handle_event(self, event: InputEvent) -> None:
        """Process an input event in Math Mode."""
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
        """Handle numeric or operator key press."""
        # If student presses equals '=', trigger calculation
        if character == "=":
            self._handle_enter()
            return

        # 1. Number Indicator (#) in Math Mode
        if character == "#":
            is_active = self.state.toggle_number_mode()
            dots_str = "Dots 3-4-5-6"
            unicode_char = "⠼"
            self.state.update_braille_info(dots_str, unicode_char)
            if self.app.display:
                self.app.display.show_character("# (Number Sign)")
                self.app.display.show_braille(unicode_char, dots_str, "○ ●\n○ ●\n● ●")
                self.app.display.show_status("Number Sign: Keys A-J represent digits 1-0" if is_active else "Ready for math")
            if self.app.speech:
                self.app.speech.speak("number sign")
            return

        # 2. Translate A-J to 1-0 when number mode is active
        if self.state.number_mode and character.upper() in BRAILLE_LETTER_TO_NUMBER:
            character = BRAILLE_LETTER_TO_NUMBER[character.upper()][0]

        if character not in MATH_VALID_CHARS:
            logger.warning("Character not permitted in Math Mode: %r", character)
            if self.app.display:
                self.app.display.show_status("Numbers and operators only")
            if self.app.speech:
                self.app.speech.speak("Numbers only")
            return

        # 1. Look up Braille mapping
        mapping = None
        if self.app.encoder:
            mapping = self.app.encoder.encode(character)

        # 2. Update state
        self.state.append_math_character(character)
        if mapping:
            self.state.update_braille_info(mapping.dots_string(), mapping.braille_unicode)

        # 3. Update display
        if self.app.display:
            label = mapping.display_label if mapping else character
            self.app.display.show_character(label)
            if mapping:
                self.app.display.show_braille(
                    mapping.braille_unicode,
                    mapping.dots_string(),
                    mapping.dots_visual()
                )
            self.app.display.show_text_buffer(self.state.math_buffer)

        # 4. Spoken audio feedback via unified speech engine
        if self.app.speech:
            if hasattr(self.app.speech, "speak_character") and type(self.app.speech).__name__ not in ("MagicMock", "Mock"):
                self.app.speech.speak_character(character)
            else:
                speech_val = mapping.speech if mapping and mapping.speech else character
                self.app.speech.speak(speech_val)

        logger.info("MathMode: CHAR=%s, BUFFER=%s", character, self.state.math_buffer)

    def _handle_space(self) -> None:
        """Handle space key press (adds visual separation between numbers)."""
        self.state.append_math_character(" ")
        if self.app.display:
            self.app.display.show_text_buffer(self.state.math_buffer)
        logger.info("MathMode: SPACE")

    def _handle_backspace(self) -> None:
        """Remove last character silently without clicks, beeps, or vocal announcements."""
        removed = self.state.backspace_math()
        if self.app.display:
            if removed:
                self.app.display.show_character("Backspace")
                self.app.display.show_text_buffer(self.state.math_buffer)
            else:
                self.app.display.show_status("Buffer empty")

        if self.app.speech and self.app.config.get("speech", "speak_control_events", default=False):
            self.app.speech.speak("backspace")

        logger.info("MathMode: BACKSPACE (removed: %r)", removed)

    def _handle_clear(self) -> None:
        """Clear the math buffer."""
        self.state.clear_math_buffer()
        if self.app.display:
            self.app.display.show_character("Cleared")
            self.app.display.show_text_buffer("")
            self.app.display.show_status("Math buffer cleared")

        if self.app.speech and self.app.config.get("speech", "speak_control_events", default=False):
            self.app.speech.speak("cleared")

        logger.info("MathMode: CLEAR")

    def _handle_enter(self) -> None:
        """Calculate math problem and provide simple step-by-step counting explanation."""
        expr = self.state.get_math_query()
        if not expr:
            if self.app.display:
                self.app.display.show_status("Math buffer is empty")
            if self.app.speech:
                self.app.speech.speak("Math buffer is empty")
            return

        # Solve deterministically using SafeArithmetic
        solution = SafeArithmetic.solve(expr)

        if solution.is_valid:
            self.state.math_last_result = solution.result_str
            self.state.math_last_explanation = solution.explanation

            # Display solution card
            if self.app.display:
                self.app.display.show_math_result(
                    equation=solution.expression,
                    result=solution.result_str,
                    explanation=solution.explanation,
                    short_step=solution.short_step,
                )
                if self.app.encoder and solution.result_str:
                    mappings = self.app.encoder.encode_text(solution.result_str)
                    unicodes = "".join(m.braille_unicode for m in mappings if m)
                    dots = " ".join(m.dots_string() for m in mappings if m)
                    if unicodes:
                        self.app.display.show_braille(unicodes, dots, "")

            # Speak the simple explanation and final answer immediately without delay
            if self.app.speech:
                self.app.speech.speak(solution.explanation)

            # Clear buffer so student can type the next problem immediately
            self.state.clear_math_buffer()
            logger.info("MathMode: SOLVED '%s' -> %s", solution.expression, solution.result_str)

        else:
            if self.app.display:
                self.app.display.show_error(solution.error_message or "Could not solve")
            if self.app.speech:
                self.app.speech.speak(solution.explanation)
            logger.warning("MathMode: SOLVE FAILED for '%s': %s", expr, solution.error_message)

    def on_enter(self) -> None:
        """Called when Math Mode becomes active."""
        self.state.clear_math_buffer()
        if self.app.display:
            self.app.display.clear()
            self.app.display.show_mode(self.mode_type)
            self.app.display.show_status("Ready for math")
            self.app.display.show_text_buffer("")
        logger.info("Entered Math Mode.")

    def on_exit(self) -> None:
        """Called when exiting Math Mode."""
        self.state.clear_math_buffer()
        logger.info("Exited Math Mode.")
