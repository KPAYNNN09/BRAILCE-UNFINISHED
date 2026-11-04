"""
Brailce Application State
===========================

Maintains the mutable runtime state of the application.

All components (modes, display, speech, logging) read from and
write to this central state object rather than maintaining their
own independent state.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from brailce.core.events import AppMode


@dataclass
class ApplicationState:
    """
    Central application state.

    Attributes:
        mode:               Current application mode.
        text_buffer:        The accumulated text from character presses.
        last_character:     The most recently pressed character.
        last_braille_dots:  Braille dot pattern for the last character.
        last_braille_unicode: Unicode Braille symbol for the last character.
        volume:             Speech volume level (0–100).
        session_id:         Unique identifier for this runtime session.
        ai_query_buffer:    Text buffer specifically for AI mode input.
        ai_last_response:   The most recent AI assistant response.
        ai_processing:      Whether an AI request is currently in progress.
        error_message:      Current error message, if any.
        is_running:         Whether the application is still active.
    """

    # Mode
    mode: AppMode = AppMode.FREE_INPUT

    # Text state
    text_buffer: str = ""
    last_character: Optional[str] = None
    last_braille_dots: Optional[str] = None
    last_braille_unicode: Optional[str] = None

    # Audio
    volume: int = 75

    # Session
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # AI state
    ai_query_buffer: str = ""
    ai_last_response: str = ""
    ai_processing: bool = False

    # Math state
    math_buffer: str = ""
    math_last_result: Optional[str] = None
    math_last_explanation: Optional[str] = None

    # Number indicator state (Grade 1 / UEB: # switches A-J to 1-0)
    number_mode: bool = False

    # System
    error_message: Optional[str] = None
    is_running: bool = True

    # ---- Text Buffer Operations ----

    def append_character(self, char: str) -> None:
        """Append a character to the text buffer."""
        self.text_buffer += char
        self.last_character = char

    def backspace(self) -> Optional[str]:
        """
        Remove and return the last character from the text buffer.
        Returns None if the buffer is empty.
        """
        if not self.text_buffer:
            return None
        removed = self.text_buffer[-1]
        self.text_buffer = self.text_buffer[:-1]
        self.last_character = self.text_buffer[-1] if self.text_buffer else None
        return removed

    def clear_buffer(self) -> None:
        """Clear the entire text buffer."""
        self.text_buffer = ""
        self.last_character = None
        self.last_braille_dots = None
        self.last_braille_unicode = None
        self.number_mode = False

    # ---- Math Buffer Operations ----

    def append_math_character(self, char: str) -> None:
        """Append a character to the math buffer."""
        self.math_buffer += char

    def backspace_math(self) -> Optional[str]:
        """
        Remove and return the last character from the math buffer.
        Returns None if the buffer is empty.
        """
        if not self.math_buffer:
            return None
        removed = self.math_buffer[-1]
        self.math_buffer = self.math_buffer[:-1]
        return removed

    def clear_math_buffer(self) -> None:
        """Clear the math buffer."""
        self.math_buffer = ""
        self.number_mode = False

    def get_math_query(self) -> str:
        """Return the current math buffer content."""
        return self.math_buffer.strip()

    # ---- AI Buffer Operations ----

    def append_ai_character(self, char: str) -> None:
        """Append a character to the AI query buffer."""
        self.ai_query_buffer += char

    def clear_ai_buffer(self) -> None:
        """Clear the AI query buffer."""
        self.ai_query_buffer = ""
        self.number_mode = False

    def get_ai_query(self) -> str:
        """Return the current AI query and clear the buffer."""
        query = self.ai_query_buffer.strip()
        self.ai_query_buffer = ""
        return query

    # ---- Number Mode Operations ----

    def toggle_number_mode(self) -> bool:
        """Toggle number mode on/off."""
        self.number_mode = not self.number_mode
        return self.number_mode

    def set_number_mode(self, active: bool) -> None:
        """Set number mode state."""
        self.number_mode = active

    # ---- Mode Operations ----

    def toggle_mode(self) -> AppMode:
        """
        Cycle between FREE_INPUT, MATH, AI_ASSISTANT, and SCANNER.
        Returns the new mode.
        """
        self.number_mode = False
        if self.mode == AppMode.FREE_INPUT:
            self.mode = AppMode.MATH
        elif self.mode == AppMode.MATH:
            self.mode = AppMode.AI_ASSISTANT
        elif self.mode == AppMode.AI_ASSISTANT:
            self.mode = AppMode.SCANNER
        else:
            self.mode = AppMode.FREE_INPUT
        return self.mode

    # ---- Volume Operations ----

    def increase_volume(self, step: int = 10) -> int:
        """Increase volume by step, capped at 100."""
        self.volume = min(100, self.volume + step)
        return self.volume

    def decrease_volume(self, step: int = 10) -> int:
        """Decrease volume by step, floored at 0."""
        self.volume = max(0, self.volume - step)
        return self.volume

    # ---- Braille Display Helpers ----

    def update_braille_info(
        self,
        dots: Optional[str],
        unicode_char: Optional[str],
    ) -> None:
        """Update the Braille representation for the last pressed character."""
        self.last_braille_dots = dots
        self.last_braille_unicode = unicode_char

    # ---- Error ----

    def set_error(self, message: str) -> None:
        """Set the current error message."""
        self.error_message = message

    def clear_error(self) -> None:
        """Clear the current error message."""
        self.error_message = None
