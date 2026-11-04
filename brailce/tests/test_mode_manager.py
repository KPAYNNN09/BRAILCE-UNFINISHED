"""
Brailce Phase 1 Tests – Mode Manager
========================================

Tests for mode switching and listener notifications.
"""

import pytest

from brailce.core.events import AppMode
from brailce.core.mode_manager import ModeManager
from brailce.core.state import ApplicationState


class TestModeManager:
    """Tests for ModeManager."""

    def test_initial_mode_is_free_input(self) -> None:
        state = ApplicationState()
        manager = ModeManager(state)
        assert manager.current_mode == AppMode.FREE_INPUT

    def test_toggle_to_math(self) -> None:
        state = ApplicationState()
        manager = ModeManager(state)
        new_mode = manager.toggle()
        assert new_mode == AppMode.MATH
        assert manager.current_mode == AppMode.MATH

    def test_toggle_back_to_free_input(self) -> None:
        state = ApplicationState()
        manager = ModeManager(state)
        manager.toggle()  # -> MATH
        manager.toggle()  # -> AI_ASSISTANT
        manager.toggle()  # -> SCANNER
        new_mode = manager.toggle()  # -> FREE_INPUT
        assert new_mode == AppMode.FREE_INPUT

    def test_listener_is_called_on_toggle(self) -> None:
        state = ApplicationState()
        manager = ModeManager(state)

        calls: list = []
        manager.register_listener(lambda old, new: calls.append((old, new)))

        manager.toggle()
        assert len(calls) == 1
        assert calls[0] == (AppMode.FREE_INPUT, AppMode.MATH)

    def test_multiple_listeners(self) -> None:
        state = ApplicationState()
        manager = ModeManager(state)

        calls_a: list = []
        calls_b: list = []
        manager.register_listener(lambda o, n: calls_a.append(n))
        manager.register_listener(lambda o, n: calls_b.append(n))

        manager.toggle()
        assert len(calls_a) == 1
        assert len(calls_b) == 1

    def test_unregister_listener(self) -> None:
        state = ApplicationState()
        manager = ModeManager(state)

        calls: list = []
        listener = lambda o, n: calls.append(n)
        manager.register_listener(listener)
        manager.unregister_listener(listener)

        manager.toggle()
        assert len(calls) == 0

    def test_listener_error_does_not_crash(self) -> None:
        state = ApplicationState()
        manager = ModeManager(state)

        def bad_listener(old: AppMode, new: AppMode) -> None:
            raise RuntimeError("Listener error")

        manager.register_listener(bad_listener)

        # Should not raise
        new_mode = manager.toggle()
        assert new_mode == AppMode.MATH
