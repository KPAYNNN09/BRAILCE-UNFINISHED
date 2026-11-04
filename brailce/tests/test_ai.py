"""
Brailce Phase 7 Tests – AI Assistant
=========================================

Tests the Ollama API client and the AIAssistantMode.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from brailce.ai.ollama_client import OllamaClient
from brailce.core.app import BrailceApp
from brailce.core.events import EventType, InputEvent
from brailce.modes.ai_assistant import AIAssistantMode
from brailce.braille.models import BrailleMapping


class TestOllamaClient:
    def test_is_available_success(self) -> None:
        client = OllamaClient()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            
            assert client.is_available() is True

    def test_is_available_failure(self) -> None:
        client = OllamaClient()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Connection refused")
            assert client.is_available() is False

    def test_generate_success(self) -> None:
        client = OllamaClient()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps({"response": "Hello world"}).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            
            result = client.generate("Say hello")
            assert result == "Hello world"

    def test_generate_empty_prompt(self) -> None:
        client = OllamaClient()
        assert client.generate("") is None
        assert client.generate("   ") is None

    def test_generate_api_error(self) -> None:
        client = OllamaClient()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 500
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            
            assert client.generate("test") is None


@pytest.fixture
def mock_app() -> BrailceApp:
    app = MagicMock(spec=BrailceApp)
    app.state = MagicMock()
    app.state.ai_query_buffer = ""
    app.state.ai_processing = False
    app.state.number_mode = False
    app.display = MagicMock()
    app.speech = MagicMock()
    app.encoder = MagicMock()
    app.ai_client = MagicMock()
    
    app.config = MagicMock()
    app.config.get.return_value = True
    
    return app


@pytest.fixture
def ai_mode(mock_app: BrailceApp) -> AIAssistantMode:
    return AIAssistantMode(mock_app)


class TestAIAssistantMode:
    def test_handle_character(self, ai_mode: AIAssistantMode, mock_app: BrailceApp) -> None:
        mock_mapping = BrailleMapping("A", "A", speech="A")
        mock_app.encoder.encode.return_value = mock_mapping
        
        event = InputEvent(EventType.CHARACTER_PRESSED, "A")
        ai_mode.handle_event(event)
        
        mock_app.state.append_ai_character.assert_called_once_with("A")
        mock_app.display.show_character.assert_called_once_with("A")
        mock_app.speech.speak.assert_called_once_with("A")

    def test_handle_space(self, ai_mode: AIAssistantMode, mock_app: BrailceApp) -> None:
        mock_app.state.ai_query_buffer = "What"
        event = InputEvent(EventType.SPACE_PRESSED)
        ai_mode.handle_event(event)
        
        mock_app.state.append_ai_character.assert_called_once_with(" ")
        mock_app.display.show_character.assert_called_once_with("Space")
        mock_app.speech.speak.assert_called_once_with("What")

    def test_handle_backspace(self, ai_mode: AIAssistantMode, mock_app: BrailceApp) -> None:
        mock_app.state.ai_query_buffer = "Hi"
        
        event = InputEvent(EventType.BACKSPACE_PRESSED)
        ai_mode.handle_event(event)
        
        assert mock_app.state.ai_query_buffer == "H"
        mock_app.display.show_character.assert_called_once_with("Backspace")

    def test_handle_clear(self, ai_mode: AIAssistantMode, mock_app: BrailceApp) -> None:
        event = InputEvent(EventType.CLEAR_PRESSED)
        ai_mode.handle_event(event)
        
        mock_app.state.clear_ai_buffer.assert_called_once()
        mock_app.display.show_character.assert_called_once_with("Cleared")

    def test_handle_enter_valid_query(self, ai_mode: AIAssistantMode, mock_app: BrailceApp) -> None:
        mock_app.state.get_ai_query.return_value = "What is Braille?"
        
        with patch("threading.Thread.start") as mock_start:
            event = InputEvent(EventType.ENTER_PRESSED)
            ai_mode.handle_event(event)
            
            assert mock_app.state.ai_processing is True
            mock_app.display.show_ai_processing.assert_called_once()
            mock_start.assert_called_once()

    def test_handle_enter_invalid_query(self, ai_mode: AIAssistantMode, mock_app: BrailceApp) -> None:
        mock_app.state.get_ai_query.return_value = ""
        
        with patch("threading.Thread.start") as mock_start:
            event = InputEvent(EventType.ENTER_PRESSED)
            ai_mode.handle_event(event)
            
            assert mock_app.state.ai_processing is False
            mock_start.assert_not_called()
            mock_app.display.show_error.assert_called_once()
            
    def test_process_query_success(self, ai_mode: AIAssistantMode, mock_app: BrailceApp) -> None:
        mock_app.ai_client.generate.return_value = "Braille is a tactile writing system."
        
        ai_mode._process_query("What is it?")
        
        assert mock_app.state.ai_processing is False
        assert mock_app.state.ai_last_response == "Braille is a tactile writing system."
        mock_app.display.show_ai_response.assert_called_once_with("Braille is a tactile writing system.")
        mock_app.speech.speak.assert_called_with("Braille is a tactile writing system.")

    def test_ignore_events_while_processing(self, ai_mode: AIAssistantMode, mock_app: BrailceApp) -> None:
        mock_app.state.ai_processing = True
        
        event = InputEvent(EventType.CHARACTER_PRESSED, "A")
        ai_mode.handle_event(event)
        
        mock_app.state.append_ai_character.assert_not_called()
