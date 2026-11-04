"""
Brailce Display – Abstract Base
=================================

All display drivers implement this interface.
The application never depends on a specific display technology.

Concrete implementations:
    - ConsoleDisplay     (laptop development)
    - ILI9488Display     (future 3.5" SPI TFT on Raspberry Pi)
    - MockDisplay        (unit testing)
"""

from __future__ import annotations

import abc
from typing import Optional

from brailce.core.events import AppMode


class DisplayDevice(abc.ABC):
    """Abstract interface for all display devices."""

    @abc.abstractmethod
    def initialize(self) -> None:
        """Initialize the display hardware/surface."""

    @abc.abstractmethod
    def shutdown(self) -> None:
        """Release display resources."""

    @abc.abstractmethod
    def show_mode(self, mode: AppMode) -> None:
        """Display the current application mode."""

    @abc.abstractmethod
    def show_character(self, character: str) -> None:
        """Display the most recently pressed character."""

    @abc.abstractmethod
    def show_braille(
        self,
        unicode_char: str,
        dots_string: str,
        dots_visual: str,
    ) -> None:
        """Display the Braille representation of the current character."""

    @abc.abstractmethod
    def show_text_buffer(self, text: str) -> None:
        """Display the accumulated text buffer."""

    @abc.abstractmethod
    def show_ai_response(self, response: str, query: Optional[str] = None) -> None:
        """Display an AI assistant response."""

    @abc.abstractmethod
    def show_ai_processing(self, query: Optional[str] = None) -> None:
        """Show a processing/loading indicator for AI requests."""

    @abc.abstractmethod
    def show_status(self, message: str) -> None:
        """Display a status message (e.g. volume, battery, errors)."""

    @abc.abstractmethod
    def show_error(self, message: str) -> None:
        """Display an error message to the user."""

    @abc.abstractmethod
    def clear(self) -> None:
        """Clear all display content."""

    def show_camera_preview(
        self, frame: Any, status: Optional[str] = None
    ) -> None:
        """
        Display a live camera viewfinder/preview frame.
        Default implementation is a no-op for displays without image preview.
        """
        pass

    def close_camera_preview(self) -> None:
        """Close or clear the camera viewfinder/preview window."""
        pass

    def show_math_result(
        self,
        equation: str,
        result: str,
        explanation: str,
        short_step: Optional[str] = None,
    ) -> None:
        """
        Display the math equation, answer, and pedagogical step explanation.
        Default implementation is a no-op.
        """
        pass

    @property
    @abc.abstractmethod
    def driver_name(self) -> str:
        """Human-readable name for this display driver."""
