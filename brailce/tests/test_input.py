"""
Brailce Phase 3 Tests – Input Simulation
===========================================

Tests for the KeyboardInputDevice and MockInputDevice.
"""

import sys
import pytest
from unittest.mock import MagicMock, patch

from brailce.core.events import AppMode, EventType, InputEvent
from brailce.input.keyboard_input import KeyboardInputDevice
from brailce.input.mock_input import MockInputDevice


class TestMockInputDevice:
    """Tests for MockInputDevice."""

    def test_start_stop(self) -> None:
        device = MockInputDevice()
        assert not device.is_running
        
        device.start()
        assert device.is_running
        
        device.stop()
        assert not device.is_running

    def test_simulate_event_emits_when_running(self) -> None:
        device = MockInputDevice()
        received = []
        device.register_callback(lambda e: received.append(e))
        
        device.start()
        event = InputEvent(EventType.CHARACTER_PRESSED, "A")
        device.simulate_event(event)
        
        assert len(received) == 1
        assert received[0].character == "A"

    def test_simulate_event_ignored_when_stopped(self) -> None:
        device = MockInputDevice()
        received = []
        device.register_callback(lambda e: received.append(e))
        
        # Not started yet
        event = InputEvent(EventType.CHARACTER_PRESSED, "A")
        device.simulate_event(event)
        
        assert len(received) == 0


class TestKeyboardInputDevice:
    """Tests for KeyboardInputDevice mapping logic."""

    @pytest.fixture
    def device(self) -> KeyboardInputDevice:
        """Create a device without actually starting the keyboard hook."""
        dev = KeyboardInputDevice(mode_getter=lambda: AppMode.FREE_INPUT)
        dev._running = True  # Pretend it's running so it processes events
        return dev

    def test_character_key_press(self, device: KeyboardInputDevice) -> None:
        received = []
        device.register_callback(lambda e: received.append(e))
        
        # Simulate 'keyboard' library event
        mock_event = MagicMock()
        mock_event.name = "a"
        
        device._on_key_press(mock_event)
        
        assert len(received) == 1
        assert received[0].event_type == EventType.CHARACTER_PRESSED
        assert received[0].character == "A"

    def test_number_key_press(self, device: KeyboardInputDevice) -> None:
        received = []
        device.register_callback(lambda e: received.append(e))
        
        mock_event = MagicMock()
        mock_event.name = "5"
        
        device._on_key_press(mock_event)
        
        assert len(received) == 1
        assert received[0].event_type == EventType.CHARACTER_PRESSED
        assert received[0].character == "5"

    def test_math_key_press(self, device: KeyboardInputDevice) -> None:
        received = []
        device.register_callback(lambda e: received.append(e))
        
        mock_event = MagicMock()
        mock_event.name = "+"
        
        device._on_key_press(mock_event)
        
        assert len(received) == 1
        assert received[0].event_type == EventType.CHARACTER_PRESSED
        assert received[0].character == "+"

    def test_space_key_press(self, device: KeyboardInputDevice) -> None:
        received = []
        device.register_callback(lambda e: received.append(e))
        
        mock_event = MagicMock()
        mock_event.name = "space"
        
        device._on_key_press(mock_event)
        
        assert len(received) == 1
        assert received[0].event_type == EventType.SPACE_PRESSED

    def test_f1_key_press_triggers_mode(self, device: KeyboardInputDevice) -> None:
        received = []
        device.register_callback(lambda e: received.append(e))
        
        mock_event = MagicMock()
        mock_event.name = "f1"
        
        device._on_key_press(mock_event)
        
        assert len(received) == 1
        assert received[0].event_type == EventType.MODE_PRESSED

    def test_unsupported_key_ignored(self, device: KeyboardInputDevice) -> None:
        received = []
        device.register_callback(lambda e: received.append(e))
        
        mock_event = MagicMock()
        mock_event.name = "shift"
        
        device._on_key_press(mock_event)
        
        assert len(received) == 0

    @patch("brailce.input.keyboard_input.kb", create=True)
    def test_start_hooks_keyboard(self, mock_kb: MagicMock) -> None:
        """Test that start() registers the keyboard hook."""
        # Need to mock the import of 'keyboard'
        with patch.dict(sys.modules, {'keyboard': mock_kb}):
            dev = KeyboardInputDevice()
            dev.start()
            
            assert dev._running is True
            mock_kb.on_press.assert_called_once_with(dev._on_key_press, suppress=False)

    @patch("brailce.input.keyboard_input.kb", create=True)
    def test_stop_unhooks_keyboard(self, mock_kb: MagicMock) -> None:
        """Test that stop() unregisters hooks."""
        with patch.dict(sys.modules, {'keyboard': mock_kb}):
            dev = KeyboardInputDevice()
            dev._running = True
            dev.stop()
            
            assert dev._running is False
            mock_kb.unhook_all.assert_called_once()
