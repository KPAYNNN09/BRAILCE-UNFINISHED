"""
Brailce Phase 1 Tests – Events
=================================

Tests for the core event model: event types, event creation,
and event factory helpers.
"""

import time
import pytest

from brailce.core.events import (
    AppMode,
    EventType,
    InputEvent,
    character_event,
    control_event,
)


class TestAppMode:
    """Tests for AppMode enum."""

    def test_free_input_display_name(self) -> None:
        assert AppMode.FREE_INPUT.display_name() == "Free Input Mode"

    def test_ai_assistant_display_name(self) -> None:
        assert AppMode.AI_ASSISTANT.display_name() == "AI Assistant Mode"

    def test_math_display_name(self) -> None:
        assert AppMode.MATH.display_name() == "Math Mode"

    def test_scanner_display_name(self) -> None:
        assert AppMode.SCANNER.display_name() == "Scanner Mode"

    def test_all_four_modes(self) -> None:
        assert len(AppMode) == 4


class TestEventType:
    """Tests for EventType enum."""

    def test_character_pressed_exists(self) -> None:
        assert EventType.CHARACTER_PRESSED is not None

    def test_all_control_events_exist(self) -> None:
        required = [
            EventType.SPACE_PRESSED,
            EventType.BACKSPACE_PRESSED,
            EventType.CLEAR_PRESSED,
            EventType.MODE_PRESSED,
            EventType.ENTER_PRESSED,
            EventType.VOLUME_UP,
            EventType.VOLUME_DOWN,
            EventType.QUIT,
            EventType.ERROR,
        ]
        assert len(required) == 9


class TestInputEvent:
    """Tests for InputEvent dataclass."""

    def test_character_event_creation(self) -> None:
        event = InputEvent(
            event_type=EventType.CHARACTER_PRESSED,
            character="A",
            source="test",
        )
        assert event.event_type == EventType.CHARACTER_PRESSED
        assert event.character == "A"
        assert event.source == "test"
        assert event.timestamp > 0

    def test_character_event_requires_character(self) -> None:
        """CHARACTER_PRESSED without a character must raise ValueError."""
        with pytest.raises(ValueError, match="CHARACTER_PRESSED"):
            InputEvent(
                event_type=EventType.CHARACTER_PRESSED,
                character=None,
                source="test",
            )

    def test_control_event_creation(self) -> None:
        event = InputEvent(
            event_type=EventType.SPACE_PRESSED,
            source="test",
        )
        assert event.event_type == EventType.SPACE_PRESSED
        assert event.character is None

    def test_event_is_frozen(self) -> None:
        event = InputEvent(
            event_type=EventType.CHARACTER_PRESSED,
            character="B",
        )
        with pytest.raises(AttributeError):
            event.character = "C"  # type: ignore[misc]


class TestEventFactories:
    """Tests for character_event() and control_event() helpers."""

    def test_character_event_uppercase(self) -> None:
        """character_event() should normalize letters to uppercase."""
        event = character_event("a", "keyboard")
        assert event.character == "A"
        assert event.event_type == EventType.CHARACTER_PRESSED
        assert event.source == "keyboard"

    def test_character_event_digit(self) -> None:
        event = character_event("5", "keyboard")
        assert event.character == "5"

    def test_character_event_math(self) -> None:
        event = character_event("+", "keyboard")
        assert event.character == "+"

    def test_control_event_space(self) -> None:
        event = control_event(EventType.SPACE_PRESSED, "keyboard")
        assert event.event_type == EventType.SPACE_PRESSED
        assert event.character is None

    def test_control_event_rejects_character_pressed(self) -> None:
        """control_event() must not accept CHARACTER_PRESSED."""
        with pytest.raises(ValueError, match="character_event"):
            control_event(EventType.CHARACTER_PRESSED, "keyboard")
