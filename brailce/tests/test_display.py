"""
Brailce Phase 6 Tests – Console Display
========================================

Tests the ConsoleDisplay output formatting.
"""

from unittest.mock import patch
import pytest

from brailce.core.events import AppMode
from brailce.display.console_display import ConsoleDisplay


class TestConsoleDisplay:
    @pytest.fixture
    def display(self) -> ConsoleDisplay:
        # Disable ANSI colors in tests to make output assertions easier
        display = ConsoleDisplay(use_colors=False)
        # Force it to think colors are disabled just in case
        display._use_colors = False
        return display

    def test_driver_name(self, display: ConsoleDisplay) -> None:
        assert display.driver_name == "Console Display (Terminal)"

    def test_show_mode(self, display: ConsoleDisplay, capsys) -> None:
        display.show_mode(AppMode.FREE_INPUT)
        
        captured = capsys.readouterr()
        assert "[MODE]" in captured.out
        assert "Free Input Mode" in captured.out

    def test_show_character(self, display: ConsoleDisplay, capsys) -> None:
        display.show_character("A")
        
        captured = capsys.readouterr()
        assert "[CHARACTER]" in captured.out
        assert "A" in captured.out

    def test_show_braille(self, display: ConsoleDisplay, capsys) -> None:
        display.show_braille("⠁", "Dot 1", "●○\n○○\n○○")
        
        captured = capsys.readouterr()
        assert "[BRAILLE]" in captured.out
        assert "Unicode : ⠁" in captured.out
        assert "Dots    : Dot 1" in captured.out
        assert "●○" in captured.out

    def test_show_text_buffer_with_text(self, display: ConsoleDisplay, capsys) -> None:
        display.show_text_buffer("HELLO")
        
        captured = capsys.readouterr()
        assert "[TEXT BUFFER]" in captured.out
        assert "HELLO" in captured.out

    def test_show_text_buffer_empty(self, display: ConsoleDisplay, capsys) -> None:
        display.show_text_buffer("")
        
        captured = capsys.readouterr()
        assert "[TEXT BUFFER]" in captured.out
        assert "(empty)" in captured.out

    def test_show_ai_response(self, display: ConsoleDisplay, capsys) -> None:
        display.show_ai_response("This is Braille.")
        
        captured = capsys.readouterr()
        assert "[AI RESPONSE]" in captured.out
        assert "This is Braille." in captured.out

    def test_show_ai_processing(self, display: ConsoleDisplay, capsys) -> None:
        display.show_ai_processing()
        
        captured = capsys.readouterr()
        assert "[AI]" in captured.out
        assert "Processing" in captured.out

    def test_show_status(self, display: ConsoleDisplay, capsys) -> None:
        display.show_status("Volume: 80")
        
        captured = capsys.readouterr()
        assert "[STATUS]" in captured.out
        assert "Volume: 80" in captured.out

    def test_show_error(self, display: ConsoleDisplay, capsys) -> None:
        display.show_error("API not responding")
        
        captured = capsys.readouterr()
        # show_error prints to stderr
        assert "[ERROR]" in captured.err
        assert "API not responding" in captured.err

    def test_show_math_mode(self, display: ConsoleDisplay, capsys) -> None:
        display.show_mode(AppMode.MATH)
        captured = capsys.readouterr()
        assert "Math Mode" in captured.out
        assert "Type math problem" in captured.out

    def test_show_math_result(self, display: ConsoleDisplay, capsys) -> None:
        display.show_math_result(
            equation="5 + 3",
            result="8",
            explanation="Start at 5, and count up 3 more: 6, 7, 8. The answer is 8.",
            short_step="Start 5 -> 6, 7, 8"
        )
        captured = capsys.readouterr()
        assert "MATH SOLUTION (GRADE 1)" in captured.out
        assert "5 + 3 = 8" in captured.out
        assert "Start 5 -> 6, 7, 8" in captured.out
        assert "Start at 5, and count up 3 more" in captured.out

    @patch("os.system")
    def test_clear_windows(self, mock_system, display: ConsoleDisplay) -> None:
        with patch("sys.stdout.isatty", return_value=True):
            with patch("os.name", "nt"):
                display.clear()
                mock_system.assert_called_once_with("cls")

    @patch("os.system")
    def test_clear_posix(self, mock_system, display: ConsoleDisplay) -> None:
        with patch("sys.stdout.isatty", return_value=True):
            with patch("os.name", "posix"):
                display.clear()
                mock_system.assert_called_once_with("clear")
