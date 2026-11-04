"""
Brailce GPIO Keypad Input Device – Future Raspberry Pi Hardware
================================================================

STUB for the future physical dedicated-character keypad.

This file defines the interface and placeholder for the Raspberry Pi
GPIO-based keypad driver that will be implemented when hardware is
available.

The GPIO driver must convert physical button presses into the same
logical InputEvent objects as the KeyboardInputDevice, ensuring
that the application pipeline is completely hardware-independent.

Expected hardware variations:
    - Individual GPIO inputs (one pin per button)
    - Key matrix (rows × columns with scanning)
    - GPIO expander (I2C-based, e.g. MCP23017)

The exact electrical implementation is configured through config.json.
The application never sees GPIO pin numbers, matrix coordinates,
or pull-up/pull-down details.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from brailce.core.events import EventType, InputEvent, character_event, control_event
from brailce.input.base import InputDevice

logger = logging.getLogger(__name__)


class GPIOKeypadInputDevice(InputDevice):
    """
    Future GPIO-based dedicated character keypad for Raspberry Pi.

    NOT YET IMPLEMENTED — requires physical hardware.

    This stub exists so the architecture is complete and the class
    can be referenced in configuration and factory code.

    When implemented, this driver will:
        1. Read GPIO pins or scan a key matrix.
        2. Debounce physical buttons.
        3. Map physical button position → character.
        4. Emit CharacterPressed / control events.
    """

    SOURCE_NAME = "gpio_keypad"

    def __init__(self, gpio_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Args:
            gpio_config: GPIO/keypad configuration from config.json.
        """
        super().__init__()
        self._gpio_config = gpio_config or {}
        logger.info(
            "GPIOKeypadInputDevice created (stub — hardware not available)."
        )

    @property
    def device_name(self) -> str:
        return "GPIO Dedicated Character Keypad (Raspberry Pi)"

    def start(self) -> None:
        """
        Start GPIO keypad listening.

        Raises:
            NotImplementedError: Always, until hardware is available.
        """
        raise NotImplementedError(
            "GPIOKeypadInputDevice is not yet implemented. "
            "Physical hardware (Raspberry Pi + keypad) is required. "
            "Use KeyboardInputDevice for laptop simulation."
        )

    def stop(self) -> None:
        """Stop GPIO keypad listening."""
        logger.info("GPIOKeypadInputDevice stopped (stub).")

    # ---- Future Implementation Sketch ----
    #
    # def _scan_matrix(self) -> Optional[str]:
    #     """Scan the key matrix and return pressed character, if any."""
    #     ...
    #
    # def _debounce(self, pin: int) -> bool:
    #     """Return True if the button press is stable (debounced)."""
    #     ...
    #
    # def _map_pin_to_character(self, pin: int) -> Optional[str]:
    #     """Look up the character assigned to a GPIO pin/matrix position."""
    #     ...
