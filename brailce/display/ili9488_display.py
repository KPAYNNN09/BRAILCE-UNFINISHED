"""
Brailce ILI9488 TFT Display – Raspberry Pi (480x320 SPI)
==========================================================

Enhanced visual display driver featuring:
- Premium modern dark design system (Tailwind-inspired slate palette)
- Dynamic battery percentage widget (UPS HAT ready / 100% plugged state)
- Mode-aware header pills with vibrant accents
- Beautiful Braille dot matrices, AI Assistant cards, and Math solution cards
- Thread-safe SPI rendering with tear-free camera preview for Scanner Mode
"""

from __future__ import annotations

import logging
import threading
from typing import Optional, Any

from brailce.core.events import AppMode
from brailce.display.base import DisplayDevice

logger = logging.getLogger(__name__)


class LgpioShim:
    """Raspberry Pi 5 RP1 compatible GPIO shim for luma.core using native lgpio."""
    OUT = 1
    IN = 0
    HIGH = 1
    LOW = 0
    BCM = 11
    BOARD = 10

    def __init__(self, chip: int = 4) -> None:
        import lgpio
        self._lgpio = lgpio
        try:
            self._h = lgpio.gpiochip_open(chip)
        except Exception:
            self._h = lgpio.gpiochip_open(0)

    def setmode(self, mode: int) -> None:
        pass

    def setup(self, pin: int, mode: int) -> None:
        try:
            self._lgpio.gpio_claim_output(self._h, pin)
        except Exception:
            pass

    def output(self, pin: int, value: int) -> None:
        try:
            self._lgpio.gpio_write(self._h, pin, 1 if value else 0)
        except Exception:
            pass

    def cleanup(self, pin: Optional[int] = None) -> None:
        pass


class NoopBacklight:
    """Callable dummy backlight to prevent luma from claiming GPIO 18 (used by I2S audio)."""
    def __call__(self, val: bool = True) -> None:
        pass

    def cleanup(self) -> None:
        pass


class ILI9488Display(DisplayDevice):
    """
    ILI9488 SPI TFT display driver for Raspberry Pi (3.5", 480x320).
    Renders rich UI cards, Braille dot matrices, mode indicators,
    battery percentage, and live camera preview frames.
    """

    def __init__(
        self,
        width: int = 480,
        height: int = 320,
        fb_path: Optional[str] = None,
        gpio_dc: int = 24,
        gpio_rst: int = 25,
        spi_port: int = 0,
        spi_device: int = 0,
    ) -> None:
        import os
        self._width = width
        self._height = height
        self._current_mode: Optional[AppMode] = None
        self._gpio_dc = gpio_dc
        self._gpio_rst = gpio_rst
        self._spi_port = spi_port
        self._spi_device = spi_device
        self._device = None  # luma.lcd device for direct SPI
        self._hardware_type = "canvas"
        self._init_error = None
        self._display_lock = threading.Lock()
        self._power_monitor: Optional[Any] = None
        self._current_query: str = ""
        self._last_status_msg: str = "Ready"

        if fb_path:
            self._fb_path = fb_path
        elif os.path.exists("/dev/fb1"):
            self._fb_path = "/dev/fb1"
        elif os.path.exists("/dev/fb0"):
            self._fb_path = "/dev/fb0"
        else:
            self._fb_path = "/dev/fb1"
        self._bpp = 16
        self._fb_file = None
        self._image = None
        self._draw = None

    @property
    def driver_name(self) -> str:
        return f"ILI9488 TFT (3.5\" 480x320, {self._hardware_type.upper()})"

    def set_power_monitor(self, monitor: Any) -> None:
        """Attach a power monitor to query live battery percentage."""
        self._power_monitor = monitor

    def initialize(self) -> None:
        """Initialize direct SPI connection, framebuffer, or buffer canvas."""
        import os
        try:
            from PIL import Image, ImageDraw
            self._image = Image.new("RGB", (self._width, self._height), color=(11, 15, 25))
            self._draw = ImageDraw.Draw(self._image)
            logger.info("ILI9488Display canvas initialized (%dx%d).", self._width, self._height)
        except ImportError:
            logger.warning("Pillow not installed; running in fallback mode.")

        # 1. Attempt direct SPI communication via luma.lcd (Primary for Raspberry Pi 5)
        if os.path.exists(f"/dev/spidev{self._spi_port}.{self._spi_device}"):
            for driver_mod in ["ili9488", "ili9486"]:
                if self._device is not None:
                    break
                try:
                    from luma.core.interface.serial import spi
                    import luma.lcd.device as devices
                    if hasattr(devices, driver_mod):
                        driver_cls = getattr(devices, driver_mod)
                        gpio_backend = LgpioShim(chip=4)
                        serial = spi(
                            port=self._spi_port,
                            device=self._spi_device,
                            gpio_DC=self._gpio_dc,
                            gpio_RST=self._gpio_rst,
                            bus_speed_hz=8000000,
                            gpio=gpio_backend,
                        )
                        # ILI9488 natively requires landscape (480, 320) with rotate=0
                        self._device = driver_cls(
                            serial,
                            width=480,
                            height=320,
                            rotate=0,
                            gpio=gpio_backend,
                            backlight=NoopBacklight(),
                        )
                        self._hardware_type = f"spi-{driver_mod}"
                        logger.info(
                            "%s connected via direct SPI (DC=GPIO%d, RST=GPIO%d).",
                            driver_mod.upper(), self._gpio_dc, self._gpio_rst
                        )
                except Exception as exc:
                    self._init_error = f"{driver_mod}: {exc}"
                    logger.warning("Direct SPI init with %s failed: %s", driver_mod, exc)

        # 2. Framebuffer fallback
        if not self._device and os.path.exists(self._fb_path):
            try:
                self._fb_file = open(self._fb_path, "wb")
                fb_id = os.path.basename(self._fb_path)
                bpp_path = f"/sys/class/graphics/{fb_id}/bits_per_pixel"
                if os.path.exists(bpp_path):
                    with open(bpp_path, "r") as f:
                        self._bpp = int(f.read().strip())
                elif self._fb_path == "/dev/fb0":
                    self._bpp = 32
                else:
                    self._bpp = 16
                self._hardware_type = "framebuffer"
                logger.info("Connected to framebuffer %s (%d bpp).", self._fb_path, self._bpp)
            except Exception as exc:
                logger.warning("Could not open %s: %s", self._fb_path, exc)

    def shutdown(self) -> None:
        if self._device:
            try:
                self._device.cleanup()
            except Exception:
                pass
        if self._fb_file:
            try:
                self._fb_file.close()
            except Exception:
                pass
        logger.info("ILI9488Display shut down.")

    def save_screenshot(self, output_path: str = "lcd_preview.png") -> bool:
        if self._image:
            try:
                self._image.save(output_path)
                return True
            except Exception as exc:
                logger.warning("Could not save screenshot: %s", exc)
        return False

    def _flush_to_hardware(self) -> None:
        """Thread-safe blit of the current image buffer to the TFT via direct SPI."""
        if not self._image:
            return

        with self._display_lock:
            # Direct SPI via luma.lcd (Raspberry Pi 5)
            if self._device is not None:
                try:
                    self._device.display(self._image)
                    return
                except Exception as exc:
                    logger.debug("Direct SPI display error: %s", exc)

            # Linux Framebuffer fallback
            if self._fb_file:
                try:
                    if self._bpp == 16:
                        pixels = self._image.getdata()
                        buf = bytearray(self._width * self._height * 2)
                        idx = 0
                        for r, g, b in pixels:
                            p = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
                            buf[idx] = p & 0xFF
                            buf[idx + 1] = (p >> 8) & 0xFF
                            idx += 2
                        raw_bytes = bytes(buf)
                    elif self._bpp == 32:
                        raw_bytes = self._image.convert("RGBA").tobytes()
                    else:
                        raw_bytes = self._image.tobytes()

                    self._fb_file.seek(0)
                    self._fb_file.write(raw_bytes)
                    self._fb_file.flush()
                except Exception as exc:
                    logger.debug("Framebuffer write error: %s", exc)

    # =========================================================================
    # Visual Design System – Headers, Badges & Battery Widget
    # =========================================================================

    def _get_battery_info(self) -> tuple[int, bool]:
        """Fetch battery percentage and plugged/charging state."""
        if self._power_monitor:
            try:
                status = self._power_monitor.get_status()
                pct = status.percentage if status.percentage is not None else 100
                charging = bool(status.is_charging or status.is_plugged_in)
                return max(0, min(100, pct)), charging
            except Exception:
                pass
        return 100, True  # Default: 100% plugged directly into power supply

    def _draw_header(self, mode: AppMode) -> None:
        """
        Render a modern, sleek top header bar:
        - Mode Pill Badge with vibrant color accent
        - Device Branding '✦ BRAILCE'
        - Battery Indicator Widget with percentage and charging icon
        """
        if not self._draw:
            return

        # Header background (deep slate navy #0F172A)
        self._draw.rectangle([(0, 0), (self._width, 46)], fill=(15, 23, 42))

        # Mode styling parameters (badge_bg, outline_color, text_color, title)
        mode_meta = {
            AppMode.FREE_INPUT: ((6, 78, 59), (16, 185, 129), (52, 211, 153), "⌨ FREE INPUT"),
            AppMode.MATH: ((120, 53, 15), (245, 158, 11), (251, 191, 36), "🔢 MATH MODE"),
            AppMode.AI_ASSISTANT: ((91, 33, 182), (139, 92, 246), (192, 132, 252), "🤖 AI ASSISTANT"),
            AppMode.SCANNER: ((21, 94, 117), (6, 182, 212), (56, 189, 248), "📷 SCANNER"),
        }
        badge_bg, accent_color, text_color, badge_text = mode_meta.get(
            mode, ((55, 65, 81), (156, 163, 175), (255, 255, 255), "BRAILCE")
        )

        # 2px bottom accent line matching mode
        self._draw.line([(0, 45), (self._width, 45)], fill=accent_color, width=2)

        # 1. Left: Mode pill badge
        pill_w = 148
        self._draw.rectangle([(12, 10), (12 + pill_w, 36)], fill=badge_bg, outline=accent_color, width=1)
        self._draw.text((22, 16), badge_text, fill=text_color)

        # 2. Center: Brand Logo
        self._draw.text((200, 16), "✦ BRAILCE", fill=(255, 255, 255))

        # 3. Right: Battery Indicator Widget
        pct, is_charging = self._get_battery_info()
        batt_x, batt_y = 385, 15
        batt_w, batt_h = 28, 14

        # Battery body outline
        batt_color = (16, 185, 129) if pct > 20 else (239, 68, 68)  # Green or Red
        self._draw.rectangle([(batt_x, batt_y), (batt_x + batt_w, batt_y + batt_h)], outline=batt_color, width=1)
        # Battery positive terminal cap
        self._draw.rectangle([(batt_x + batt_w, batt_y + 4), (batt_x + batt_w + 3, batt_y + batt_h - 4)], fill=batt_color)

        # Fill level inside battery
        fill_w = max(1, int((batt_w - 4) * (pct / 100.0)))
        self._draw.rectangle([(batt_x + 2, batt_y + 2), (batt_x + 2 + fill_w, batt_y + batt_h - 2)], fill=batt_color)

        # Percentage text & charging bolt
        bolt = "⚡" if is_charging else ""
        batt_label = f"{pct}%{bolt}"
        self._draw.text((batt_x + batt_w + 7, batt_y + 1), batt_label, fill=(226, 232, 240))

    # =========================================================================
    # Operating Modes Rendering
    # =========================================================================

    def show_mode(self, mode: AppMode) -> None:
        """Switch mode and draw initial layout."""
        self._current_mode = mode
        self._current_query = ""
        if not self._draw:
            return

        # Clear background to deep midnight canvas (#0B0F19)
        self._draw.rectangle([(0, 0), (self._width, self._height)], fill=(11, 15, 25))
        self._draw_header(mode)

        # Initial guidance card based on mode
        if mode == AppMode.FREE_INPUT:
            self.show_character(" ")
            self.show_text_buffer("")
        elif mode == AppMode.MATH:
            self._draw_math_welcome()
        elif mode == AppMode.AI_ASSISTANT:
            self.show_ai_query_input("")
        elif mode == AppMode.SCANNER:
            self.show_scanner_viewfinder()

        self._flush_to_hardware()

    def _draw_math_welcome(self) -> None:
        """Math mode starting card."""
        self._draw.rectangle([(15, 56), (465, 276)], fill=(15, 23, 42), outline=(245, 158, 11), width=2)
        self._draw.text((30, 72), "GRADE 1 ARITHMETIC TUTOR:", fill=(251, 191, 36))
        self._draw.text((30, 105), "Type a single-digit math problem (0 to 9)", fill=(255, 255, 255))
        self._draw.text((30, 135), "Examples:  2 + 3   |   7 - 4   |   5 + 5", fill=(148, 163, 184))
        self._draw.text((30, 180), "• Press ENTER to calculate and hear counting steps", fill=(203, 213, 225))
        self._draw.text((30, 210), "• Press CLEAR to reset equation buffer", fill=(148, 163, 184))
        self.show_status("Ready for math input (0-9, +, -)")

    # -------------------------------------------------------------------------
    # Free Input Mode
    # -------------------------------------------------------------------------

    def show_character(self, character: str) -> None:
        if not self._draw:
            return
        if self._current_mode == AppMode.AI_ASSISTANT:
            return

        # Character card (Top Left)
        self._draw.rectangle([(15, 56), (195, 175)], fill=(15, 23, 42), outline=(16, 185, 129), width=1)
        self._draw.text((25, 68), "ACTIVE CHARACTER:", fill=(52, 211, 153))
        display_char = character if character.strip() else "[Space]"
        self._draw.text((25, 105), display_char, fill=(255, 255, 255))
        self._flush_to_hardware()

    def show_braille(
        self, unicode_char: str, dots_string: str, dots_visual: str
    ) -> None:
        if not self._draw or self._current_mode == AppMode.AI_ASSISTANT:
            return
        import re

        # Braille cell card (Top Right)
        self._draw.rectangle([(205, 56), (465, 175)], fill=(15, 23, 42), outline=(16, 185, 129), width=1)
        self._draw.text((215, 68), f"BRAILLE: {unicode_char}", fill=(255, 255, 255))
        self._draw.text((215, 96), f"Dots: {dots_string[:20]}", fill=(148, 163, 184))

        # Render 6-dot matrix cell (2x3)
        cell_x, cell_y = 400, 78
        dot_r = 7
        dot_dx, dot_dy = 22, 22
        coords = {
            1: (cell_x, cell_y),
            2: (cell_x, cell_y + dot_dy),
            3: (cell_x, cell_y + 2 * dot_dy),
            4: (cell_x + dot_dx, cell_y),
            5: (cell_x + dot_dx, cell_y + dot_dy),
            6: (cell_x + dot_dx, cell_y + 2 * dot_dy),
        }
        active_dots = set(int(d) for d in re.findall(r'\b[1-6]\b', dots_string))
        for dot_num, (cx, cy) in coords.items():
            if dot_num in active_dots:
                self._draw.ellipse([(cx - dot_r, cy - dot_r), (cx + dot_r, cy + dot_r)], fill=(251, 191, 36))
            else:
                self._draw.ellipse([(cx - dot_r, cy - dot_r), (cx + dot_r, cy + dot_r)], outline=(71, 85, 105), width=2)

        self._flush_to_hardware()

    def show_text_buffer(self, text: str) -> None:
        if not self._draw:
            return
        if self._current_mode == AppMode.AI_ASSISTANT:
            self.show_ai_query_input(text)
            return

        import textwrap
        # Buffer card (Bottom)
        self._draw.rectangle([(15, 185), (465, 276)], fill=(15, 23, 42), outline=(51, 65, 85), width=1)
        self._draw.text((25, 195), "ACCUMULATED SENTENCE BUFFER:", fill=(148, 163, 184))

        buf_display = text if text else "(Empty - type letters to practice)"
        lines = textwrap.wrap(buf_display, width=44)
        y = 220
        for line in lines[:2]:
            self._draw.text((25, y), line, fill=(255, 255, 255))
            y += 20

        # Cursor
        if text:
            cx = min(440, 25 + len(lines[-1]) * 8)
            self._draw.rectangle([(cx, y - 18), (cx + 5, y - 4)], fill=(251, 191, 36))

        self.show_status(f"Letters: {len(text)} | Press Space for word, Enter for sentence")
        self._flush_to_hardware()

    # -------------------------------------------------------------------------
    # AI Assistant Mode
    # -------------------------------------------------------------------------

    def show_ai_query_input(self, query: str) -> None:
        """Render modern AI query input card with golden cursor."""
        if not self._draw:
            return
        import textwrap
        self._current_query = query

        # Clear working canvas
        self._draw.rectangle([(0, 47), (self._width, self._height - 35)], fill=(11, 15, 25))

        # Question card (Top)
        self._draw.rectangle([(15, 56), (465, 170)], fill=(15, 23, 42), outline=(139, 92, 246), width=2)
        self._draw.text((25, 66), "YOUR QUESTION (AI ASSISTANT):", fill=(192, 132, 252))

        if query:
            lines = textwrap.wrap(query, width=44)
            y = 96
            for line in lines[:3]:
                self._draw.text((25, y), line, fill=(255, 255, 255))
                y += 22
            cx = min(440, 25 + len(lines[-1]) * 8)
            self._draw.rectangle([(cx, y - 20), (cx + 6, y - 4)], fill=(251, 191, 36))
        else:
            self._draw.text((25, 102), "Type your question on the Braille keypad...", fill=(100, 116, 139))
            self._draw.text((25, 128), "Examples: WHAT IS RAIN?  |  TELL A STORY", fill=(71, 85, 105))

        # Helper card (Bottom)
        self._draw.rectangle([(15, 180), (465, 276)], fill=(15, 23, 42), outline=(51, 65, 85), width=1)
        self._draw.text((25, 192), "CONTROLS & HINTS:", fill=(251, 191, 36))
        self._draw.text((25, 216), "• Press ENTER to ask the AI", fill=(203, 213, 225))
        self._draw.text((25, 240), "• Press TAB to cycle modes | BACKSPACE to delete", fill=(148, 163, 184))

        self.show_status(f"Length: {len(query)} characters | Press ENTER to ask")
        self._flush_to_hardware()

    def show_ai_processing(self, query: Optional[str] = None) -> None:
        """Render prominent purple neural inference loading card."""
        if not self._draw:
            return
        import textwrap

        self._draw.rectangle([(0, 47), (self._width, self._height - 35)], fill=(11, 15, 25))

        # Question header
        self._draw.rectangle([(15, 56), (465, 130)], fill=(15, 23, 42), outline=(139, 92, 246), width=1)
        self._draw.text((25, 66), "QUESTION:", fill=(192, 132, 252))
        q_text = query or (self._current_query or "...")
        q_lines = textwrap.wrap(q_text, width=44)
        for i, line in enumerate(q_lines[:2]):
            self._draw.text((25, 88 + i * 18), line, fill=(255, 255, 255))

        # Processing card
        self._draw.rectangle([(15, 140), (465, 276)], fill=(24, 16, 48), outline=(168, 85, 247), width=2)
        self._draw.text((30, 160), "⚡ AI IS THINKING...", fill=(251, 191, 36))
        self._draw.text((30, 192), "Running offline neural model on Raspberry Pi 5...", fill=(226, 232, 240))
        # Gradient progress bar
        self._draw.rectangle([(30, 226), (450, 244)], fill=(15, 23, 42), outline=(139, 92, 246))
        self._draw.rectangle([(30, 226), (360, 244)], fill=(168, 85, 247))

        self.show_status("AI is generating your response...")
        self._flush_to_hardware()

    def show_ai_response(self, response: str, query: Optional[str] = None) -> None:
        """Render crisp Q&A card with multi-line answer."""
        if not self._draw:
            return
        import textwrap

        self._draw.rectangle([(0, 47), (self._width, self._height - 35)], fill=(11, 15, 25))

        # Question summary (Top)
        self._draw.rectangle([(15, 56), (465, 116)], fill=(15, 23, 42), outline=(71, 85, 105), width=1)
        self._draw.text((25, 64), "QUESTION:", fill=(148, 163, 184))
        q_text = query or self._current_query
        if q_text:
            self._draw.text((25, 84), q_text[:48], fill=(255, 255, 255))
        else:
            self._draw.text((25, 84), "(Student Query)", fill=(203, 213, 225))

        # AI Answer card (Bottom)
        self._draw.rectangle([(15, 126), (465, 276)], fill=(15, 23, 42), outline=(6, 182, 212), width=2)
        self._draw.text((25, 136), "AI ANSWER:", fill=(34, 211, 238))

        lines = textwrap.wrap(response, width=44)
        y = 162
        for line in lines[:5]:
            self._draw.text((25, y), line, fill=(255, 255, 255))
            y += 20

        self.show_status("Answer complete. Press any key to type or TAB.")
        self._flush_to_hardware()

    # -------------------------------------------------------------------------
    # Math Mode
    # -------------------------------------------------------------------------

    def show_math_result(
        self,
        equation: str,
        result: str,
        explanation: str,
        short_step: Optional[str] = None,
    ) -> None:
        if not self._draw:
            return
        import textwrap

        self._draw.rectangle([(0, 47), (self._width, self._height - 35)], fill=(11, 15, 25))

        # Solution card
        self._draw.rectangle([(15, 56), (465, 276)], fill=(15, 23, 42), outline=(245, 158, 11), width=2)
        self._draw.text((25, 66), "MATH SOLUTION (GRADE 1):", fill=(251, 191, 36))
        self._draw.text((25, 92), f"Equation: {equation} = {result}", fill=(255, 255, 255))

        if short_step:
            self._draw.text((25, 118), f"Steps: {short_step[:44]}", fill=(52, 211, 153))

        self._draw.text((25, 146), "Counting Explanation:", fill=(251, 191, 36))
        exp_lines = textwrap.wrap(explanation, width=44)
        y = 170
        for line in exp_lines[:4]:
            self._draw.text((25, y), line, fill=(226, 232, 240))
            y += 20

        self.show_status(f"Solved: {equation} = {result}")
        self._flush_to_hardware()

    # -------------------------------------------------------------------------
    # Scanner Mode (Camera Viewfinder)
    # -------------------------------------------------------------------------

    def show_scanner_viewfinder(self, status: Optional[str] = None) -> None:
        """Render initial scanner instructions card."""
        if not self._draw:
            return
        self._draw.rectangle([(0, 47), (self._width, self._height - 35)], fill=(11, 15, 25))

        # Viewfinder box (Neon Emerald)
        mx, my = 35, 68
        self._draw.rectangle([(mx, my), (self._width - mx, 260)], outline=(16, 185, 129), width=2)
        self._draw.text((mx + 15, my + 15), "OPTICAL BRAILLE SCANNER (OBR)", fill=(52, 211, 153))
        self._draw.text((mx + 15, my + 45), "Place embossed Braille page inside camera box", fill=(255, 255, 255))
        self._draw.text((mx + 15, my + 78), "• Press ENTER to capture and translate page", fill=(251, 191, 36))
        self._draw.text((mx + 15, my + 108), "• Press TAB to cycle through modes", fill=(148, 163, 184))

        st = status or "Position Braille inside box | Press Enter to Scan"
        self.show_status(st)
        self._flush_to_hardware()

    def show_camera_preview(
        self, frame: Any, status: Optional[str] = None
    ) -> None:
        """Render camera preview with clean framing and battery header."""
        if frame is None or not self._image:
            return
        try:
            import cv2
            from PIL import Image, ImageDraw

            resized = cv2.resize(frame, (self._width, self._height))
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            self._image = Image.fromarray(rgb_frame)
            self._draw = ImageDraw.Draw(self._image)

            # Viewfinder frame: Emerald corners
            mx, my = int(self._width * 0.12), int(self._height * 0.15)
            bx, by = self._width - mx, self._height - my
            self._draw.rectangle([(mx, my), (bx, by)], outline=(16, 185, 129), width=3)
            # Center crosshair
            cx, cy = self._width // 2, self._height // 2
            self._draw.line([(cx - 15, cy), (cx + 15, cy)], fill=(16, 185, 129), width=2)
            self._draw.line([(cx, cy - 15), (cx, cy + 15)], fill=(16, 185, 129), width=2)

            # Header with battery widget
            self._draw_header(AppMode.SCANNER)

            # Detection Pill Badge (centered right under header)
            if status and "detected" in status.lower():
                badge_w = 320
                bx0 = (self._width - badge_w) // 2
                if "no " in status.lower() or "not" in status.lower():
                    self._draw.rectangle([(bx0, 52), (bx0 + badge_w, 76)], fill=(153, 27, 27), outline=(239, 68, 68), width=1)
                    self._draw.text((bx0 + 10, 56), status[:46], fill=(255, 255, 255))
                else:
                    self._draw.rectangle([(bx0, 52), (bx0 + badge_w, 76)], fill=(6, 95, 70), outline=(52, 211, 153), width=1)
                    self._draw.text((bx0 + 10, 56), status[:46], fill=(255, 255, 255))

            # Bottom Status Bar (solid fill to prevent text ghosting)
            st = status if status else "Position Braille inside box | Press Enter to Scan"
            self._draw.rectangle([(0, self._height - 34), (self._width, self._height)], fill=(3, 7, 18))
            self._draw.line([(0, self._height - 34), (self._width, self._height - 34)], fill=(31, 41, 55), width=1)
            self._draw.text((15, self._height - 24), f"● {st[:55]}", fill=(56, 189, 248))

            self._flush_to_hardware()
        except Exception as exc:
            logger.debug("Error updating ILI9488 camera preview: %s", exc)

    def close_camera_preview(self) -> None:
        self.clear()

    # -------------------------------------------------------------------------
    # Status & Alerts (Unified Bottom Bar Geometry)
    # -------------------------------------------------------------------------

    def show_status(self, message: str) -> None:
        """Render unified bottom status bar without ghosting."""
        if not self._draw:
            return
        self._last_status_msg = message
        self._draw.rectangle([(0, self._height - 34), (self._width, self._height)], fill=(3, 7, 18))
        self._draw.line([(0, self._height - 34), (self._width, self._height - 34)], fill=(31, 41, 55), width=1)
        self._draw.text((15, self._height - 24), f"● {message[:55]}", fill=(251, 191, 36))
        self._flush_to_hardware()

    def show_error(self, message: str) -> None:
        """Render prominent red error bar at bottom."""
        if not self._draw:
            return
        self._draw.rectangle([(0, self._height - 34), (self._width, self._height)], fill=(127, 29, 29))
        self._draw.line([(0, self._height - 34), (self._width, self._height - 34)], fill=(239, 68, 68), width=1)
        self._draw.text((15, self._height - 24), f"⚠ Error: {message[:50]}", fill=(255, 255, 255))
        self._flush_to_hardware()

    def clear(self) -> None:
        if self._draw:
            self._draw.rectangle([(0, 0), (self._width, self._height)], fill=(11, 15, 25))
            if self._current_mode:
                self.show_mode(self._current_mode)
            self._flush_to_hardware()
