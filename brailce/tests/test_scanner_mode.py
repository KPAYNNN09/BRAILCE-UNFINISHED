"""
Brailce Tests – Scanner Mode
============================

Test suite for Scanner Mode (OBR).
Verifies preview lifecycle, scan loop, and presence detection behavior.
"""

from unittest.mock import MagicMock
import pytest

from brailce.core.app import BrailceApp
from brailce.core.events import AppMode, EventType, InputEvent
from brailce.core.state import ApplicationState
from brailce.modes.scanner_mode import ScannerMode


@pytest.fixture
def mock_app() -> BrailceApp:
    """Create a mock BrailceApp with real state and mocked subsystems."""
    app = MagicMock(spec=BrailceApp)
    app.state = ApplicationState()
    app.display = MagicMock()
    app.speech = MagicMock()
    app.camera = MagicMock()
    app.obr = MagicMock()
    app.config = MagicMock()
    app.config.get.return_value = True
    return app


@pytest.fixture
def scanner_mode(mock_app: BrailceApp) -> ScannerMode:
    return ScannerMode(mock_app)


class TestScannerMode:
    """Tests for ScannerMode."""

    def test_mode_properties(self, scanner_mode: ScannerMode) -> None:
        assert scanner_mode.mode_type == AppMode.SCANNER
        assert scanner_mode.display_name == "Scanner Mode"

    def test_enter_and_exit_lifecycle(self, scanner_mode: ScannerMode, mock_app: BrailceApp) -> None:
        scanner_mode.on_enter()
        assert scanner_mode._preview_running is True
        mock_app.display.show_mode.assert_called_with(AppMode.SCANNER)

        scanner_mode.on_exit()
        assert scanner_mode._preview_running is False
        mock_app.display.close_camera_preview.assert_called_once()

    def test_clear_pressed_resets_state(self, scanner_mode: ScannerMode, mock_app: BrailceApp) -> None:
        scanner_mode.scanned_text = "ABC"
        scanner_mode._braille_detected = True
        event = InputEvent(event_type=EventType.CLEAR_PRESSED)
        scanner_mode.handle_event(event)

        assert scanner_mode.scanned_text is None
        assert scanner_mode._braille_detected is None
        mock_app.display.show_status.assert_called_with("Position Braille inside box | Press Enter to Scan")
