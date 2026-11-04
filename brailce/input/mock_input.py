"""
Brailce Mock Input Device – Testing Simulation
===============================================

Provides a mock input source for unit testing.
Allows tests to inject simulated logical events (CharacterPressed, etc.)
without requiring physical hardware or a real keyboard hook.
"""

from __future__ import annotations

import logging
from typing import Optional

from brailce.core.events import InputEvent
from brailce.input.base import InputDevice

logger = logging.getLogger(__name__)


class MockInputDevice(InputDevice):
    """
    Mock input device for testing.
    
    Exposes `simulate_event()` to allow tests to manually inject
    InputEvent objects into the application pipeline.
    """

    SOURCE_NAME = "mock"

    def __init__(self) -> None:
        super().__init__()
        self.is_running = False

    @property
    def device_name(self) -> str:
        return "Mock Input Device (Testing)"

    def start(self) -> None:
        """Mark the mock device as started."""
        self.is_running = True
        logger.info("MockInputDevice started.")

    def stop(self) -> None:
        """Mark the mock device as stopped."""
        self.is_running = False
        logger.info("MockInputDevice stopped.")

    def simulate_event(self, event: InputEvent) -> None:
        """
        Manually inject an event into the pipeline.
        
        Args:
            event: The InputEvent to emit.
        """
        if not self.is_running:
            logger.warning("MockInputDevice is not running, ignoring event: %s", event)
            return
            
        logger.debug("MockInputDevice simulating event: %s", event)
        self._emit_event(event)
