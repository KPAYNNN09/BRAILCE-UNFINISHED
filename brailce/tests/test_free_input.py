"""
Brailce Phase 4 Tests – Free Input Mode
===========================================

Tests the primary feedback loop in FreeInputMode.
"""

from unittest.mock import MagicMock
import pytest

from brailce.core.app import BrailceApp
from brailce.core.events import EventType, InputEvent
from brailce.modes.free_input import FreeInputMode
from brailce.braille.models import BrailleMapping


@pytest.fixture
def mock_app() -> BrailceApp:
    """Create a mock BrailceApp with mocked subsystems."""
    app = MagicMock(spec=BrailceApp)
    app.state = MagicMock()
    app.state.ai_processing = False
    app.state.number_mode = False
    app.display = MagicMock()
    app.speech = MagicMock()
    app.encoder = MagicMock()
    
    # Setup config dict-like mock
    app.config = MagicMock()
    app.config.get.return_value = True
    
    return app


@pytest.fixture
def free_input_mode(mock_app: BrailceApp) -> FreeInputMode:
    return FreeInputMode(mock_app)


class TestFreeInputMode:
    def test_handle_supported_character(self, free_input_mode: FreeInputMode, mock_app: BrailceApp) -> None:
        """Test the full pipeline when a valid character is pressed."""
        # Setup mock encoder return
        mock_mapping = BrailleMapping(
            character="A", 
            display_label="A", 
            braille_dots={1}, 
            braille_unicode="⠁", 
            speech="A"
        )
        mock_app.encoder.encode.return_value = mock_mapping
        mock_app.state.text_buffer = "A"

        # Fire event
        event = InputEvent(EventType.CHARACTER_PRESSED, character="A")
        free_input_mode.handle_event(event)

        # 1. Check encoder called
        mock_app.encoder.encode.assert_called_once_with("A")
        
        # 2. Check state updated
        mock_app.state.append_character.assert_called_once_with("A")
        mock_app.state.update_braille_info.assert_called_once_with("Dot 1", "⠁")
        
        # 3. Check display updated
        mock_app.display.show_character.assert_called_once_with("A")
        mock_app.display.show_braille.assert_called_once()
        mock_app.display.show_text_buffer.assert_called_once_with("A")
        
        # 4. Check speech
        mock_app.speech.speak.assert_called_once_with("A")

    def test_handle_unsupported_character(self, free_input_mode: FreeInputMode, mock_app: BrailceApp) -> None:
        """Test pipeline when an unsupported character is pressed."""
        mock_app.encoder.encode.return_value = None

        event = InputEvent(EventType.CHARACTER_PRESSED, character="Z")
        free_input_mode.handle_event(event)

        mock_app.state.append_character.assert_not_called()
        mock_app.speech.speak.assert_called_once_with("Unsupported")

    def test_handle_space(self, free_input_mode: FreeInputMode, mock_app: BrailceApp) -> None:
        """Test space button logic."""
        mock_app.state.text_buffer = "A"
        
        event = InputEvent(EventType.SPACE_PRESSED)
        free_input_mode.handle_event(event)

        mock_app.state.append_character.assert_called_once_with(" ")
        mock_app.display.show_character.assert_called_once_with("Space")
        mock_app.speech.speak.assert_called_once_with("A")

    def test_handle_backspace_with_content(self, free_input_mode: FreeInputMode, mock_app: BrailceApp) -> None:
        """Test backspace button logic when buffer has text."""
        mock_app.state.backspace.return_value = "B"
        
        event = InputEvent(EventType.BACKSPACE_PRESSED)
        free_input_mode.handle_event(event)

        mock_app.display.show_character.assert_called_once_with("Backspace")
        mock_app.speech.speak.assert_called_once_with("backspace")

    def test_handle_backspace_empty(self, free_input_mode: FreeInputMode, mock_app: BrailceApp) -> None:
        """Test backspace button logic when buffer is empty."""
        mock_app.state.backspace.return_value = None
        
        event = InputEvent(EventType.BACKSPACE_PRESSED)
        free_input_mode.handle_event(event)

        mock_app.display.show_status.assert_called_once_with("Buffer empty")
        mock_app.speech.speak.assert_called_once_with("backspace")

    def test_handle_clear(self, free_input_mode: FreeInputMode, mock_app: BrailceApp) -> None:
        """Test clear button logic."""
        event = InputEvent(EventType.CLEAR_PRESSED)
        free_input_mode.handle_event(event)

        mock_app.state.clear_buffer.assert_called_once()
        mock_app.display.show_character.assert_called_once_with("Cleared")
        mock_app.display.show_text_buffer.assert_called_once_with("")
        mock_app.speech.speak.assert_called_once_with("cleared")

    def test_hash_toggles_number_mode(self, free_input_mode: FreeInputMode, mock_app: BrailceApp) -> None:
        """Test pressing '#' toggles number mode and updates display and speech."""
        mock_app.state.toggle_number_mode.return_value = True
        event = InputEvent(EventType.CHARACTER_PRESSED, character="#")
        free_input_mode.handle_event(event)

        mock_app.state.toggle_number_mode.assert_called_once()
        mock_app.speech.speak.assert_called_once_with("number sign, number mode on")
        mock_app.display.show_character.assert_called_with("# (Number Sign)")

    def test_number_mode_translates_a_to_j_to_digits(self, free_input_mode: FreeInputMode, mock_app: BrailceApp) -> None:
        """When number mode is active, pressing A-J produces 1-0."""
        mock_app.state.number_mode = True
        event = InputEvent(EventType.CHARACTER_PRESSED, character="A")
        free_input_mode.handle_event(event)

        mock_app.state.append_character.assert_called_once_with("1")
        mock_app.speech.speak.assert_called_once_with("one")
        mock_app.display.show_character.assert_called_once_with("1 (from A)")

    def test_space_terminates_number_mode(self, free_input_mode: FreeInputMode, mock_app: BrailceApp) -> None:
        """Pressing space in number mode resets it back to letter mode."""
        mock_app.state.number_mode = True
        mock_app.state.text_buffer = "12 "
        event = InputEvent(EventType.SPACE_PRESSED)
        free_input_mode.handle_event(event)
        assert mock_app.state.number_mode is False

    def test_handle_enter(self, free_input_mode: FreeInputMode, mock_app: BrailceApp) -> None:
        """Test enter speaks the sentence and refreshes the buffer."""
        mock_app.state.text_buffer = "cat"
        event = InputEvent(EventType.ENTER_PRESSED)
        free_input_mode.handle_event(event)

        mock_app.speech.speak.assert_called_once_with("cat", interrupt=False)
        mock_app.state.clear_buffer.assert_called_once()
        mock_app.display.show_text_buffer.assert_called_once_with("")
