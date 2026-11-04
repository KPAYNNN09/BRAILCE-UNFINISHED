"""
Brailce Mode Manager
=====================

Manages transitions between application modes.

Currently supports exactly two modes:
    - FREE_INPUT
    - AI_ASSISTANT

The MODE button (physical or simulated) triggers toggle_mode(),
which updates the application state and notifies registered listeners.
"""

from __future__ import annotations

import logging
from typing import Callable, List

from brailce.core.events import AppMode
from brailce.core.state import ApplicationState

logger = logging.getLogger(__name__)

# Type alias for mode-change listeners
ModeChangeListener = Callable[[AppMode, AppMode], None]


class ModeManager:
    """
    Manages mode transitions and notifies listeners.

    Attributes:
        state:      Reference to the shared application state.
        _listeners: Callbacks invoked on every mode change.
    """

    def __init__(self, state: ApplicationState) -> None:
        self.state = state
        self._listeners: List[ModeChangeListener] = []

    @property
    def current_mode(self) -> AppMode:
        """Return the current application mode."""
        return self.state.mode

    def toggle(self) -> AppMode:
        """
        Switch to the next mode and notify all listeners.

        Returns:
            The newly active mode.
        """
        old_mode = self.state.mode
        new_mode = self.state.toggle_mode()

        logger.info("Mode changed: %s → %s", old_mode.name, new_mode.name)

        for listener in self._listeners:
            try:
                listener(old_mode, new_mode)
            except Exception:
                logger.exception(
                    "Error in mode-change listener: %s", listener
                )

        return new_mode

    def register_listener(self, listener: ModeChangeListener) -> None:
        """Register a callback to be invoked on mode transitions."""
        self._listeners.append(listener)

    def unregister_listener(self, listener: ModeChangeListener) -> None:
        """Remove a previously registered mode-change listener."""
        try:
            self._listeners.remove(listener)
        except ValueError:
            logger.warning("Listener not found for removal: %s", listener)
