"""
Brailce Core Event Model
=========================

Defines the logical events that flow through the application pipeline.

Physical or simulated input devices produce these events.
The application logic consumes them without knowledge of the
underlying hardware (GPIO, keyboard, etc.).

Pipeline:
    Physical/Simulated Button → InputDevice → LogicalEvent → ApplicationMode
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Application Modes
# ---------------------------------------------------------------------------

class AppMode(Enum):
    """The supported application modes."""
    FREE_INPUT = auto()
    MATH = auto()
    AI_ASSISTANT = auto()
    SCANNER = auto()

    def display_name(self) -> str:
        """Human-readable mode name for speech and display."""
        names = {
            AppMode.FREE_INPUT: "Free Input Mode",
            AppMode.MATH: "Math Mode",
            AppMode.AI_ASSISTANT: "AI Assistant Mode",
            AppMode.SCANNER: "Scanner Mode",
        }
        return names[self]


# ---------------------------------------------------------------------------
# Event Types
# ---------------------------------------------------------------------------

class EventType(Enum):
    """
    All logical event types the application can receive.

    CHARACTER_PRESSED is the primary event for dedicated character buttons.
    Control events handle navigation, mode switching, and volume.
    """
    # Primary character input
    CHARACTER_PRESSED = auto()

    # Control events
    SPACE_PRESSED = auto()
    BACKSPACE_PRESSED = auto()
    CLEAR_PRESSED = auto()
    MODE_PRESSED = auto()
    ENTER_PRESSED = auto()
    VOLUME_UP = auto()
    VOLUME_DOWN = auto()

    # System events
    QUIT = auto()
    ERROR = auto()


# ---------------------------------------------------------------------------
# Event Data Classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InputEvent:
    """
    A single logical input event.

    Every physical button press or simulated key press is converted
    into an InputEvent by the input device driver.

    Attributes:
        event_type:  The kind of event (CHARACTER_PRESSED, SPACE_PRESSED, etc.)
        character:   The character associated with the event, if applicable.
                     For CHARACTER_PRESSED, this is the character itself (e.g. "A").
                     For control events, this may be None.
        timestamp:   When the event was created (seconds since epoch).
        source:      Identifies the input source (e.g. "keyboard", "gpio").
        raw_data:    Optional raw data from the hardware layer for diagnostics.
    """
    event_type: EventType
    character: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    raw_data: Optional[Any] = None

    def __post_init__(self) -> None:
        """Validate event consistency."""
        if self.event_type == EventType.CHARACTER_PRESSED and not self.character:
            raise ValueError(
                "CHARACTER_PRESSED events must include a character value."
            )


# ---------------------------------------------------------------------------
# Event Callback Type
# ---------------------------------------------------------------------------

# Type alias for event handler callbacks
EventCallback = type(None)  # Placeholder; actual typing below

from typing import Callable
EventCallback = Callable[[InputEvent], None]


# ---------------------------------------------------------------------------
# Factory Helpers
# ---------------------------------------------------------------------------

def character_event(char: str, source: str = "unknown") -> InputEvent:
    """Create a CHARACTER_PRESSED event for a single character."""
    return InputEvent(
        event_type=EventType.CHARACTER_PRESSED,
        character=char.upper() if char.isalpha() else char,
        source=source,
    )


def control_event(event_type: EventType, source: str = "unknown") -> InputEvent:
    """Create a control event (SPACE, BACKSPACE, CLEAR, MODE, etc.)."""
    if event_type == EventType.CHARACTER_PRESSED:
        raise ValueError(
            "Use character_event() for CHARACTER_PRESSED events."
        )
    return InputEvent(
        event_type=event_type,
        source=source,
    )
