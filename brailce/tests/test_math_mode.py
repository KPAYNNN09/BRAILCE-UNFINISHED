"""
Brailce Tests – Math Mode
==========================

Test suite for dedicated Math Mode (Method 1).
Verifies keypad interaction, buffer management, solver invocation,
speech generation, and error handling.
"""

from unittest.mock import MagicMock, patch
import pytest

from brailce.braille.models import BrailleMapping
from brailce.core.app import BrailceApp
from brailce.core.events import AppMode, EventType, InputEvent
from brailce.core.state import ApplicationState
from brailce.modes.math_mode import MathMode


@pytest.fixture
def mock_app() -> BrailceApp:
    """Create a mock BrailceApp with real state and mocked subsystems."""
    app = MagicMock(spec=BrailceApp)
    app.state = ApplicationState()
    app.display = MagicMock()
    app.speech = MagicMock()
    app.encoder = MagicMock()
    app.config = MagicMock()
    app.config.get.return_value = True
    return app


@pytest.fixture
def math_mode(mock_app: BrailceApp) -> MathMode:
    return MathMode(mock_app)


class TestMathMode:
    """Tests for MathMode."""

    def test_mode_properties(self, math_mode: MathMode) -> None:
        assert math_mode.mode_type == AppMode.MATH
        assert math_mode.display_name == "Math Mode"

    def test_handle_digit_input(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        mapping = BrailleMapping(
            character="5",
            display_label="5",
            braille_dots={2, 6},
            braille_unicode="⠢",
            speech="five"
        )
        mock_app.encoder.encode.return_value = mapping

        event = InputEvent(EventType.CHARACTER_PRESSED, character="5")
        math_mode.handle_event(event)

        assert mock_app.state.math_buffer == "5"
        mock_app.display.show_character.assert_called_with("5")
        mock_app.display.show_text_buffer.assert_called_with("5")
        mock_app.speech.speak.assert_called_with("five")

    def test_handle_operator_input(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        mapping = BrailleMapping(
            character="+",
            display_label="+",
            braille_dots={3, 4, 6},
            braille_unicode="⠬",
            speech="plus"
        )
        mock_app.encoder.encode.return_value = mapping

        event = InputEvent(EventType.CHARACTER_PRESSED, character="+")
        math_mode.handle_event(event)

        assert mock_app.state.math_buffer == "+"
        mock_app.speech.speak.assert_called_with("plus")

    def test_handle_space(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        mock_app.state.math_buffer = "5"
        event = InputEvent(EventType.SPACE_PRESSED)
        math_mode.handle_event(event)

        assert mock_app.state.math_buffer == "5 "
        mock_app.display.show_text_buffer.assert_called_with("5 ")

    def test_handle_backspace(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        mock_app.state.math_buffer = "5+"
        event = InputEvent(EventType.BACKSPACE_PRESSED)
        math_mode.handle_event(event)

        assert mock_app.state.math_buffer == "5"
        mock_app.display.show_character.assert_called_with("Backspace")
        mock_app.speech.speak.assert_called_with("backspace")

    def test_handle_clear(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        mock_app.state.math_buffer = "12+5"
        event = InputEvent(EventType.CLEAR_PRESSED)
        math_mode.handle_event(event)

        assert mock_app.state.math_buffer == ""
        mock_app.display.show_character.assert_called_with("Cleared")
        mock_app.speech.speak.assert_called_with("cleared")

    def test_solve_valid_addition_on_enter(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        mock_app.state.math_buffer = "5 + 3"
        event = InputEvent(EventType.ENTER_PRESSED)
        math_mode.handle_event(event)

        # Result stored
        assert mock_app.state.math_last_result == "8"
        assert "Start at 5, and count up 3 more: 6, 7, 8" in mock_app.state.math_last_explanation

        # Display called
        mock_app.display.show_math_result.assert_called_once()
        args = mock_app.display.show_math_result.call_args[1]
        assert args["equation"] == "5 + 3"
        assert args["result"] == "8"

        # Speech speaks counting explanation
        mock_app.speech.speak.assert_called_once()
        spoken = mock_app.speech.speak.call_args[0][0]
        assert "Start at 5, and count up 3 more: 6, 7, 8" in spoken

        # Buffer cleared for next problem
        assert mock_app.state.math_buffer == ""

    def test_solve_triggered_by_equals_key(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        mock_app.state.math_buffer = "9 - 4"
        event = InputEvent(EventType.CHARACTER_PRESSED, character="=")
        math_mode.handle_event(event)

        assert mock_app.state.math_last_result == "5"
        mock_app.display.show_math_result.assert_called_once()
        spoken = mock_app.speech.speak.call_args[0][0]
        assert "Start at 9, and count back 4: 8, 7, 6, 5" in spoken

    def test_enter_with_empty_buffer(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        mock_app.state.math_buffer = ""
        event = InputEvent(EventType.ENTER_PRESSED)
        math_mode.handle_event(event)

        mock_app.display.show_status.assert_called_with("Math buffer is empty")
        spoken = mock_app.speech.speak.call_args[0][0]
        assert "Math buffer is empty" in spoken

    def test_solve_underflow_grade1_rejection(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        mock_app.state.math_buffer = "3 - 5"
        event = InputEvent(EventType.ENTER_PRESSED)
        math_mode.handle_event(event)

        mock_app.display.show_error.assert_called_once()
        spoken = mock_app.speech.speak.call_args[0][0]
        assert "cannot take away 5 from 3" in spoken

    def test_letters_rejected_in_math_mode(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        event = InputEvent(EventType.CHARACTER_PRESSED, character="A")
        math_mode.handle_event(event)

        assert mock_app.state.math_buffer == ""
        mock_app.speech.speak.assert_called_with("Numbers only")
        mock_app.display.show_status.assert_called_with("Numbers and operators only")

    def test_lifecycle_on_enter_and_exit(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        mock_app.state.math_buffer = "123"
        math_mode.on_enter()
        assert mock_app.state.math_buffer == ""
        mock_app.display.show_status.assert_called_with("Ready for math")

        mock_app.state.math_buffer = "456"
        math_mode.on_exit()
        assert mock_app.state.math_buffer == ""

    def test_app_setup_registers_math_mode(self) -> None:
        """Integration test: Verify BrailceApp setup registers MathMode."""
        from brailce.config.loader import ConfigLoader
        config = ConfigLoader.from_defaults()
        app = BrailceApp(config)
        with patch("brailce.core.app.SpeechService.from_config", return_value=MagicMock()):
            app.setup()

        assert AppMode.MATH in app._modes
        assert isinstance(app._modes[AppMode.MATH], MathMode)

        # Toggle to Math Mode
        app.mode_manager.toggle()
        assert app.state.mode == AppMode.MATH
        assert app._active_mode == app._modes[AppMode.MATH]

    def test_hash_number_mode_in_math_mode(self, math_mode: MathMode, mock_app: BrailceApp) -> None:
        """Pressing '#' enables number mode so keys A-J produce 1-0 in Math Mode."""
        # 1. Press '#'
        math_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="#"))
        assert mock_app.state.number_mode is True
        mock_app.speech.speak.assert_called_with("number sign")

        # 2. Press 'E' -> produces '5'
        math_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="E"))
        assert mock_app.state.math_buffer == "5"

        # 3. Press '+'
        math_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="+"))
        assert mock_app.state.math_buffer == "5+"

        # 4. Press 'C' -> produces '3'
        math_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="C"))
        assert mock_app.state.math_buffer == "5+3"
