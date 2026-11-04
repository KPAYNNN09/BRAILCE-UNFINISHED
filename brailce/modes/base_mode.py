"""
Brailce Mode – Abstract Base
===============================

Base class for application modes (Free Input, AI Assistant).
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Optional

from brailce.core.events import AppMode, InputEvent

if TYPE_CHECKING:
    from brailce.core.app import BrailceApp


class BaseMode(abc.ABC):
    """
    Abstract base for application modes.

    Each mode handles input events differently and manages
    its own portion of the user experience.
    """

    def __init__(self, app: "BrailceApp") -> None:
        self.app = app
        self.state = app.state

    @property
    @abc.abstractmethod
    def mode_type(self) -> AppMode:
        """Return the AppMode enum value for this mode."""

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        """Human-readable name for display and speech."""

    @abc.abstractmethod
    def handle_event(self, event: InputEvent) -> None:
        """Process a single input event within this mode's context."""

    @abc.abstractmethod
    def on_enter(self) -> None:
        """Called when this mode becomes active."""

    @abc.abstractmethod
    def on_exit(self) -> None:
        """Called when switching away from this mode."""
