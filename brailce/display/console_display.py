"""
Brailce Console Display – Rich Aesthetic Terminal Interface
=============================================================

A sleek, high-contrast, modern terminal dashboard for the Brailce device.
Renders cohesive Unicode card layouts, giant high-contrast Braille dots,
real-time sentence buffer with active cursor, and live status bars.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, Optional

from brailce.core.events import AppMode
from brailce.display.base import DisplayDevice

logger = logging.getLogger(__name__)


# Modern ANSI 256-color palette
class _Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Theme colors
    CYAN = "\033[38;5;51m"
    DEEP_CYAN = "\033[38;5;38m"
    EMERALD = "\033[38;5;48m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    GOLD = "\033[38;5;220m"
    AMBER = "\033[38;5;214m"
    VIOLET = "\033[38;5;141m"
    WHITE = "\033[38;5;255m"
    SLATE = "\033[38;5;244m"
    DARK_SLATE = "\033[38;5;238m"
    RED = "\033[38;5;196m"


class ConsoleDisplay(DisplayDevice):
    """
    High-contrast aesthetic console display with cohesive card rendering.
    """

    def __init__(self, use_colors: bool = True) -> None:
        self._use_colors = use_colors and self._supports_color()
        self._current_mode: Optional[AppMode] = None
        self._last_cam_print: float = 0.0

    @property
    def driver_name(self) -> str:
        return "Console Display (Terminal)"

    def initialize(self) -> None:
        if sys.platform == "win32":
            try:
                if hasattr(sys.stdout, "reconfigure"):
                    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        logger.info("ConsoleDisplay initialized.")
        c = self._c()
        print(f"\n{c.CYAN}{c.BOLD}╔════════════════════════════════════════════════════════════╗")
        print(f"║  BRAILCE ASSISTIVE SYSTEM — Console Dashboard Active       ║")
        print(f"╚════════════════════════════════════════════════════════════╝{c.RESET}\n")

    def shutdown(self) -> None:
        c = self._c()
        print(f"\n{c.VIOLET}{c.BOLD}╭────────────────────────────────────────────────────────────╮")
        print(f"│  BRAILCE ASSISTIVE DEVICE — System Offline                 │")
        print(f"╰────────────────────────────────────────────────────────────╯{c.RESET}\n")

    def _c(self):
        if self._use_colors:
            return _Colors
        return type("NoColor", (), {k: "" for k in dir(_Colors) if not k.startswith("_")})

    def show_mode(self, mode: AppMode) -> None:
        self._current_mode = mode
        mode_name = mode.display_name()
        c = self._c()
        
        instructions = {
            AppMode.FREE_INPUT: "Type on dedicated Braille keys for letter and word voice feedback.",
            AppMode.MATH: "Type math problem (e.g. 5+3) and press Enter for step-by-step counting solution.",
            AppMode.AI_ASSISTANT: "Type your question using Braille keys and press Enter to ask AI.",
            AppMode.SCANNER: "Aim camera at Braille paper and press Enter to scan."
        }.get(mode, "")

        print(f"{c.CYAN}{c.BOLD}[MODE]{c.RESET} {c.GOLD}{mode_name}{c.RESET}")
        print(f"{c.CYAN}╭────────────────────────────────────────────────────────────╮")
        print(f"│  {c.WHITE}{c.BOLD}ACTIVE MODE:{c.RESET} {c.EMERALD}{mode_name:<44}{c.CYAN}│")
        if instructions:
            print(f"│  {c.SLATE}{instructions[:56]:<56}{c.CYAN}│")
        print(f"╰────────────────────────────────────────────────────────────╯{c.RESET}\n")

    def show_character(self, character: str) -> None:
        c = self._c()
        print(f"{c.GREEN}{c.BOLD}[CHARACTER]{c.RESET} {c.EMERALD}{c.BOLD}[ {character} ]{c.RESET}")

    def show_braille(
        self,
        unicode_char: str,
        dots_string: str,
        dots_visual: str,
    ) -> None:
        c = self._c()
        print(f"{c.GREEN}{c.BOLD}[BRAILLE]{c.RESET}")
        print(f"  Unicode : {c.GOLD}{unicode_char}{c.RESET}")
        print(f"  Dots    : {c.CYAN}{dots_string}{c.RESET}")
        print(f"  Visual  :")
        for row in dots_visual.split("\n"):
            r_str = row.strip()
            if r_str:
                colored_row = r_str.replace("●", f"{c.GOLD}●{c.RESET}").replace("○", f"{c.DARK_SLATE}○{c.RESET}") if self._use_colors else r_str
                print(f"    {colored_row}")

    def show_text_buffer(self, text: str) -> None:
        c = self._c()
        display_text = text if text else "(empty)"
        cursor = f"{c.GOLD}█{c.RESET}" if text else ""
        print(f"{c.GREEN}{c.BOLD}[TEXT BUFFER]{c.RESET} {c.WHITE}{display_text}{cursor}{c.RESET}")

    def show_status(self, message: str) -> None:
        c = self._c()
        print(f"{c.GREEN}{c.BOLD}[STATUS]{c.RESET} {c.AMBER}{message}{c.RESET}")

    def show_error(self, message: str) -> None:
        c = self._c()
        print(f"{c.RED}{c.BOLD}[ERROR] {message}{c.RESET}", file=sys.stderr)

    def show_ai_response(self, response: str, query: Optional[str] = None) -> None:
        c = self._c()
        if query:
            print(f"{c.GREEN}{c.BOLD}[AI QUERY]{c.RESET} {query}")
        print(f"{c.GREEN}{c.BOLD}[AI RESPONSE]{c.RESET} {c.WHITE}{response}{c.RESET}")
        print(f"\n{c.VIOLET}{c.BOLD}╭── [ AI ASSISTANT ANSWER ] ─────────────────────────────────╮{c.RESET}")
        print(f"│  {c.WHITE}{response}{c.RESET}")
        print(f"{c.VIOLET}{c.BOLD}╰────────────────────────────────────────────────────────────╯{c.RESET}\n")

    def show_ai_processing(self, query: Optional[str] = None) -> None:
        c = self._c()
        msg = f"Processing query: {query}" if query else "Processing... please wait."
        print(f"{c.GREEN}{c.BOLD}[AI]{c.RESET} {c.GOLD}{msg}{c.RESET}")

    def show_math_result(
        self,
        equation: str,
        result: str,
        explanation: str,
        short_step: Optional[str] = None,
    ) -> None:
        c = self._c()
        print(f"\n{c.CYAN}{c.BOLD}══════════ MATH SOLUTION (GRADE 1) ══════════{c.RESET}")
        print(f"{c.GREEN}{c.BOLD}Equation   :{c.RESET} {c.YELLOW}{equation} = {result}{c.RESET}")
        if short_step:
            print(f"{c.GREEN}{c.BOLD}Count Steps:{c.RESET} {c.YELLOW}{short_step}{c.RESET}")
        print(f"{c.GREEN}{c.BOLD}Explanation:{c.RESET} {c.YELLOW}{explanation}{c.RESET}")
        print(f"{c.CYAN}{c.BOLD}══════════════════════════════════════════════{c.RESET}\n")

    def show_camera_preview(
        self, frame: Any, status: Optional[str] = None
    ) -> None:
        """Render live camera viewfinder and save snapshot."""
        if frame is None:
            return
        
        # 1. Save frame snapshot for easy viewing on laptop
        try:
            import cv2
            cv2.imwrite("camera_preview.jpg", frame)
        except Exception:
            pass

        # 2. Render live terminal viewfinder card every 1.5 seconds
        now = time.time()
        if now - self._last_cam_print > 1.5:
            self._last_cam_print = now
            c = self._c()
            st = status if status else "Position Braille inside box | Press Enter to Scan"
            print(f"\n{c.CYAN}{c.BOLD}╭── [ CAMERA VIEWFINDER: SCANNER MODE ] ─────────────────────╮{c.RESET}")
            print(f"│  {c.EMERALD}● Camera Live Feed [640x480]{c.CYAN} | Frame saved: camera_preview.jpg │")
            print(f"│  Target  : [ + ] Centered on Braille Page                  │")
            print(f"│  {c.GOLD}{st:<56}{c.CYAN}  │")
            print(f"{c.CYAN}{c.BOLD}╰────────────────────────────────────────────────────────────╯{c.RESET}")

        # 3. If local desktop window is supported, display OpenCV window
        try:
            import cv2
            cv2.imshow("Brailce - Camera Viewfinder", frame)
            cv2.waitKey(1)
        except Exception:
            pass

    def close_camera_preview(self) -> None:
        try:
            import cv2
            cv2.destroyWindow("Brailce - Camera Viewfinder")
        except Exception:
            pass

    def clear(self) -> None:
        if sys.stdout.isatty():
            os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def _supports_color() -> bool:
        if os.name == "nt":
            return True
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
