"""
Brailce Keyboard Input Device – Laptop Simulation
===================================================

Simulates the dedicated character keypad using the laptop keyboard.

IMPORTANT:
    Each laptop key press directly maps to a dedicated character button.
    Pressing 'A' on the laptop is equivalent to pressing the physical
    [A] button on the Brailce keypad.

    This is NOT a six-dot Braille combination input system.
    This is a one-key-per-character simulation.

Behavior by mode:
    FREE_INPUT:
        Each keystroke immediately generates a CHARACTER_PRESSED event.
    AI_ASSISTANT:
        Normal text input; only ENTER submits the AI query.

Threading:
    The keyboard listener runs in a background thread so it does
    not block the main application loop.
"""

from __future__ import annotations

import logging
import sys
import threading
from typing import Optional, Set

from brailce.core.events import (
    AppMode,
    EventType,
    InputEvent,
    character_event,
    control_event,
)
from brailce.input.base import InputDevice

logger = logging.getLogger(__name__)

# Characters supported as dedicated button simulations
SUPPORTED_LETTERS: Set[str] = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
SUPPORTED_DIGITS: Set[str] = set("0123456789")
SUPPORTED_MATH: Set[str] = {"+", "-", "*", "/", "="}
SUPPORTED_PUNCTUATION: Set[str] = {".", ",", "!", "?", "'", '"', ":", ";", "#"}
SUPPORTED_CHARACTERS: Set[str] = (
    SUPPORTED_LETTERS | SUPPORTED_DIGITS | SUPPORTED_MATH | SUPPORTED_PUNCTUATION
)

# Special key mappings for control events
# These keys simulate the dedicated control buttons on the physical keypad
CONTROL_KEY_MAP = {
    # Key name from the keyboard library → EventType
    "f1": EventType.MODE_PRESSED,
    "tab": EventType.MODE_PRESSED,
    "f2": EventType.CLEAR_PRESSED,
    "f11": EventType.VOLUME_DOWN,
    "f12": EventType.VOLUME_UP,
}


class KeyboardInputDevice(InputDevice):
    """
    Laptop keyboard input device.

    Converts laptop key presses into logical InputEvent objects,
    simulating the dedicated character buttons of the Brailce keypad.

    Uses the `keyboard` library for cross-platform key capture.

    Attributes:
        _mode_ref:    Callable that returns the current AppMode.
        _running:     Whether the listener is active.
        _thread:      Background thread for the keyboard listener.
    """

    SOURCE_NAME = "keyboard"

    def __init__(
        self,
        mode_getter: Optional[callable] = None,
    ) -> None:
        """
        Args:
            mode_getter: A callable returning the current AppMode.
                         Defaults to always returning FREE_INPUT.
        """
        super().__init__()
        self._mode_getter = mode_getter or (lambda: AppMode.FREE_INPUT)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def device_name(self) -> str:
        return "Laptop Keyboard (Simulation)"

    # ---- Lifecycle ----

    def start(self) -> None:
        """Start listening for keyboard events."""
        self._running = True

        # 1. Hardware hook (for physical keyboard or local desktop)
        try:
            import keyboard as kb  # noqa: F811
            kb.on_press(self._on_key_press, suppress=False)
        except Exception as exc:
            logger.debug("Raw keyboard hook unavailable or requires root: %s", exc)

        # 2. Terminal listener (for SSH / PuTTY sessions)
        if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            self._thread = threading.Thread(target=self._terminal_listener, daemon=True)
            self._thread.start()

        logger.info(
            "KeyboardInputDevice started — keys simulate dedicated character buttons."
        )

    def stop(self) -> None:
        """Stop listening for keyboard events."""
        self._running = False
        try:
            import keyboard as kb
            kb.unhook_all()
        except Exception:
            logger.debug("keyboard unhook completed or not available.")
        logger.info("KeyboardInputDevice stopped.")

    def _terminal_listener(self) -> None:
        """Read single characters from terminal (PuTTY/SSH) without requiring Enter."""
        import sys
        if sys.platform != "win32":
            try:
                import termios, tty, select
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
                try:
                    while self._running:
                        r, _, _ = select.select([sys.stdin], [], [], 0.2)
                        if r:
                            ch = sys.stdin.read(1)
                            if ch:
                                self._process_char(ch)
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except Exception as exc:
                logger.debug("Terminal listener error: %s", exc)
        else:
            try:
                import msvcrt, time
                while self._running:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        try:
                            ch_str = ch.decode("utf-8", errors="ignore")
                            if ch_str:
                                self._process_char(ch_str)
                        except Exception:
                            pass
                    time.sleep(0.05)
            except Exception as exc:
                logger.debug("Windows terminal listener error: %s", exc)

    def _process_char(self, ch: str) -> None:
        """Convert a character from terminal input to an InputEvent."""
        if ch == "\x1b":
            # Check if this is an escape sequence (e.g. F1, F2 in PuTTY)
            import sys
            seq = ""
            if sys.platform != "win32":
                try:
                    import select
                    while select.select([sys.stdin], [], [], 0.03)[0]:
                        seq += sys.stdin.read(1)
                except Exception:
                    pass
            
            if seq in ("OP", "[11~", "[[A", "O1;2P"):  # F1 key in PuTTY / xterm
                self._emit_event(control_event(EventType.MODE_PRESSED, self.SOURCE_NAME))
            elif seq in ("OQ", "[12~", "[[B", "O1;2Q"):  # F2 key in PuTTY
                self._emit_event(control_event(EventType.CLEAR_PRESSED, self.SOURCE_NAME))
            elif not seq:  # Pure ESC key
                self._emit_event(control_event(EventType.QUIT, self.SOURCE_NAME))
        elif ch in ("\t", "\x09"):  # TAB -> Switch mode!
            self._emit_event(control_event(EventType.MODE_PRESSED, self.SOURCE_NAME))
        elif ch in ("\r", "\n"):  # ENTER
            self._emit_event(control_event(EventType.ENTER_PRESSED, self.SOURCE_NAME))
        elif ch in ("\x7f", "\b"):  # Backspace
            self._emit_event(control_event(EventType.BACKSPACE_PRESSED, self.SOURCE_NAME))
        elif ch == " ":  # Space
            self._emit_event(control_event(EventType.SPACE_PRESSED, self.SOURCE_NAME))
        else:
            upper = ch.upper()
            if upper in SUPPORTED_CHARACTERS:
                self._emit_event(character_event(upper, self.SOURCE_NAME))

    # ---- Key Handling ----

    def _on_key_press(self, event: "keyboard.KeyboardEvent") -> None:  # type: ignore[name-defined]
        """
        Handle a raw keyboard event.

        Converts the laptop key into the corresponding logical
        InputEvent and dispatches it.
        """
        if not self._running:
            return

        key_name: str = event.name or ""

        # ---- Control keys ----
        if key_name.lower() == "esc":
            self._emit_event(control_event(EventType.QUIT, self.SOURCE_NAME))
            return

        if key_name.lower() in CONTROL_KEY_MAP:
            evt_type = CONTROL_KEY_MAP[key_name.lower()]
            self._emit_event(control_event(evt_type, self.SOURCE_NAME))
            return

        if key_name.lower() == "space":
            self._emit_event(
                control_event(EventType.SPACE_PRESSED, self.SOURCE_NAME)
            )
            return

        if key_name.lower() == "backspace":
            self._emit_event(
                control_event(EventType.BACKSPACE_PRESSED, self.SOURCE_NAME)
            )
            return

        if key_name.lower() == "enter":
            self._emit_event(
                control_event(EventType.ENTER_PRESSED, self.SOURCE_NAME)
            )
            return

        # ---- Character keys ----
        char = key_name.upper() if len(key_name) == 1 else key_name

        if len(char) == 1 and char in SUPPORTED_CHARACTERS:
            self._emit_event(character_event(char, self.SOURCE_NAME))
            return

        # Handle lowercase single chars
        if len(key_name) == 1:
            upper = key_name.upper()
            if upper in SUPPORTED_CHARACTERS:
                self._emit_event(character_event(upper, self.SOURCE_NAME))
                return

        # Unsupported key — log but do not crash
        logger.debug("Unsupported key ignored: %r", key_name)
