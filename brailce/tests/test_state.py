"""
Brailce Phase 1 Tests – Application State
============================================

Tests for the ApplicationState dataclass and its operations.
"""

import pytest

from brailce.core.events import AppMode
from brailce.core.state import ApplicationState


class TestTextBuffer:
    """Tests for text buffer operations."""

    def test_initial_buffer_is_empty(self) -> None:
        state = ApplicationState()
        assert state.text_buffer == ""

    def test_append_character(self) -> None:
        state = ApplicationState()
        state.append_character("A")
        assert state.text_buffer == "A"
        assert state.last_character == "A"

    def test_append_multiple_characters(self) -> None:
        state = ApplicationState()
        for char in "HELLO":
            state.append_character(char)
        assert state.text_buffer == "HELLO"
        assert state.last_character == "O"

    def test_backspace_removes_last(self) -> None:
        state = ApplicationState()
        state.append_character("A")
        state.append_character("B")
        state.append_character("C")
        removed = state.backspace()
        assert removed == "C"
        assert state.text_buffer == "AB"
        assert state.last_character == "B"

    def test_backspace_empty_buffer_returns_none(self) -> None:
        state = ApplicationState()
        removed = state.backspace()
        assert removed is None
        assert state.text_buffer == ""

    def test_clear_buffer(self) -> None:
        state = ApplicationState()
        state.append_character("A")
        state.append_character("B")
        state.clear_buffer()
        assert state.text_buffer == ""
        assert state.last_character is None

    def test_buffer_preserves_spaces_and_symbols(self) -> None:
        state = ApplicationState()
        for char in "A B+5":
            state.append_character(char)
        assert state.text_buffer == "A B+5"


class TestModeOperations:
    """Tests for mode toggling."""

    def test_initial_mode_is_free_input(self) -> None:
        state = ApplicationState()
        assert state.mode == AppMode.FREE_INPUT

    def test_toggle_to_math(self) -> None:
        state = ApplicationState()
        new_mode = state.toggle_mode()
        assert new_mode == AppMode.MATH
        assert state.mode == AppMode.MATH

    def test_full_four_mode_cycle(self) -> None:
        state = ApplicationState()
        assert state.toggle_mode() == AppMode.MATH
        assert state.toggle_mode() == AppMode.AI_ASSISTANT
        assert state.toggle_mode() == AppMode.SCANNER
        new_mode = state.toggle_mode()
        assert new_mode == AppMode.FREE_INPUT
        assert state.mode == AppMode.FREE_INPUT

    def test_four_toggles_returns_to_original(self) -> None:
        state = ApplicationState()
        state.toggle_mode()
        state.toggle_mode()
        state.toggle_mode()
        state.toggle_mode()
        assert state.mode == AppMode.FREE_INPUT


class TestMathBuffer:
    """Tests for math query buffer."""

    def test_math_buffer_initially_empty(self) -> None:
        state = ApplicationState()
        assert state.math_buffer == ""

    def test_append_math_character(self) -> None:
        state = ApplicationState()
        state.append_math_character("5")
        state.append_math_character("+")
        state.append_math_character("3")
        assert state.math_buffer == "5+3"

    def test_backspace_math(self) -> None:
        state = ApplicationState()
        assert state.backspace_math() is None
        state.append_math_character("5")
        state.append_math_character("+")
        removed = state.backspace_math()
        assert removed == "+"
        assert state.math_buffer == "5"

    def test_clear_math_buffer(self) -> None:
        state = ApplicationState()
        state.append_math_character("12-4")
        state.clear_math_buffer()
        assert state.math_buffer == ""

    def test_get_math_query(self) -> None:
        state = ApplicationState()
        state.append_math_character("  7 + 2  ")
        assert state.get_math_query() == "7 + 2"


class TestVolumeOperations:
    """Tests for volume control."""

    def test_initial_volume(self) -> None:
        state = ApplicationState()
        assert state.volume == 75

    def test_increase_volume(self) -> None:
        state = ApplicationState()
        new_vol = state.increase_volume()
        assert new_vol == 85

    def test_volume_capped_at_100(self) -> None:
        state = ApplicationState()
        state.volume = 95
        new_vol = state.increase_volume()
        assert new_vol == 100

    def test_decrease_volume(self) -> None:
        state = ApplicationState()
        new_vol = state.decrease_volume()
        assert new_vol == 65

    def test_volume_floored_at_0(self) -> None:
        state = ApplicationState()
        state.volume = 5
        new_vol = state.decrease_volume()
        assert new_vol == 0


class TestAIBuffer:
    """Tests for AI query buffer."""

    def test_ai_buffer_initially_empty(self) -> None:
        state = ApplicationState()
        assert state.ai_query_buffer == ""

    def test_append_ai_character(self) -> None:
        state = ApplicationState()
        state.append_ai_character("H")
        state.append_ai_character("i")
        assert state.ai_query_buffer == "Hi"

    def test_get_ai_query_clears_buffer(self) -> None:
        state = ApplicationState()
        state.append_ai_character("Hello")
        query = state.get_ai_query()
        assert query == "Hello"
        assert state.ai_query_buffer == ""

    def test_get_ai_query_strips_whitespace(self) -> None:
        state = ApplicationState()
        state.ai_query_buffer = "  What is Braille?  "
        query = state.get_ai_query()
        assert query == "What is Braille?"


class TestSessionAndState:
    """Tests for session and system state."""

    def test_session_id_is_generated(self) -> None:
        state = ApplicationState()
        assert state.session_id
        assert len(state.session_id) == 12

    def test_unique_session_ids(self) -> None:
        s1 = ApplicationState()
        s2 = ApplicationState()
        assert s1.session_id != s2.session_id

    def test_is_running_initially_true(self) -> None:
        state = ApplicationState()
        assert state.is_running is True

    def test_error_message(self) -> None:
        state = ApplicationState()
        state.set_error("Something went wrong")
        assert state.error_message == "Something went wrong"
        state.clear_error()
        assert state.error_message is None


class TestNumberModeOperations:
    """Tests for number_mode state toggle and auto-reset."""

    def test_initial_number_mode_is_false(self) -> None:
        state = ApplicationState()
        assert state.number_mode is False

    def test_toggle_number_mode(self) -> None:
        state = ApplicationState()
        assert state.toggle_number_mode() is True
        assert state.number_mode is True
        assert state.toggle_number_mode() is False
        assert state.number_mode is False

    def test_clear_buffer_resets_number_mode(self) -> None:
        state = ApplicationState()
        state.set_number_mode(True)
        state.clear_buffer()
        assert state.number_mode is False

    def test_toggle_mode_resets_number_mode(self) -> None:
        state = ApplicationState()
        state.set_number_mode(True)
        state.toggle_mode()
        assert state.number_mode is False

