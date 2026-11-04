"""
Brailce Input Device – Abstract Base
======================================

Defines the abstract interface that ALL input devices must implement.

This is the hardware-independence boundary:
    - The application logic receives only InputEvent objects.
    - It never knows whether events came from a laptop keyboard,
      GPIO keypad, key matrix, or test harness.

Concrete implementations:
    - KeyboardInputDevice   (laptop simulation)
    - GPIOKeypadInputDevice (future Raspberry Pi hardware)
    - MockInputDevice       (unit testing)
"""

from __future__ import annotations

import abc
from typing import Callable, Optional

from brailce.core.events import InputEvent

# Type alias for the event callback
InputEventCallback = Callable[[InputEvent], None]


class InputDevice(abc.ABC):
    """
    Abstract base class for all input devices.

    Every input device must be able to:
        - start()     : Begin listening for input events.
        - stop()      : Stop listening and release resources.
        - register_callback() : Set the function to call on each event.
    """

    def __init__(self) -> None:
        self._callback: Optional[InputEventCallback] = None

    def register_callback(self, callback: InputEventCallback) -> None:
        """
        Register the single callback that receives all input events.

        Args:
            callback: A function that accepts an InputEvent.
        """
        self._callback = callback

    def _emit_event(self, event: InputEvent) -> None:
        """
        Dispatch an event to the registered callback.

        Subclasses call this to deliver logical events to the application.
        """
        if self._callback is not None:
            self._callback(event)

    @abc.abstractmethod
    def start(self) -> None:
        """Start the input device / begin listening for events."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the input device and clean up resources."""

    @property
    @abc.abstractmethod
    def device_name(self) -> str:
        """Human-readable name for this input device."""
