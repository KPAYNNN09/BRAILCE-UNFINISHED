"""
Brailce Mode – Scanner Mode (Phase 9)
=====================================

Scanner Mode utilizes a camera and Optical Braille Recognition (OBR)
to read physical Braille paper and speak it out loud.
"""

from __future__ import annotations

import logging
import threading
import time

from typing import Optional, Any
from brailce.core.events import AppMode, EventType, InputEvent
from brailce.modes.base_mode import BaseMode

logger = logging.getLogger(__name__)

class ScannerMode(BaseMode):
    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.scanned_text: Optional[str] = None
        self._is_scanning = False
        self._preview_running = False
        self._preview_thread: Optional[threading.Thread] = None
        self._detector_thread: Optional[threading.Thread] = None
        self._latest_frame: Any = None
        self._braille_detected: Optional[bool] = None

    @property
    def mode_type(self) -> AppMode:
        return AppMode.SCANNER

    @property
    def display_name(self) -> str:
        return "Scanner Mode"

    def handle_event(self, event: InputEvent) -> None:
        """Process an input event in Scanner Mode."""
        if self.state.ai_processing or self._is_scanning:
            return

        if event.event_type == EventType.ENTER_PRESSED:
            if self.scanned_text:
                self._speak_result()
            else:
                self._start_scan()
        elif event.event_type == EventType.CLEAR_PRESSED:
            self.scanned_text = None
            self._braille_detected = None
            if self.app.display:
                self.app.display.show_status("Position Braille inside box | Press Enter to Scan")

    def _start_scan(self) -> None:
        """Trigger the scanning loop."""
        self._is_scanning = True
        self.scanned_text = None

        if self.app.speech:
            self.app.speech.speak_text("Scanning document", interrupt=False)

        threading.Thread(target=self._scan_loop, daemon=True).start()

    def _detection_worker(self) -> None:
        """Periodic background presence detector to give live feedback without lagging the preview."""
        _last_detected_state = None
        while self._preview_running:
            if not self._is_scanning and self._latest_frame is not None and getattr(self.app, "obr", None):
                try:
                    detected = self.app.obr.detect_braille_presence(self._latest_frame)
                    self._braille_detected = detected
                    # Announce detection state changes vocally
                    if detected != _last_detected_state:
                        if detected is True and self.app.speech:
                            self.app.speech.speak_text("Braille detected. Press enter to translate.", interrupt=False)
                        elif detected is False and _last_detected_state is not None and self.app.speech:
                            self.app.speech.speak_text("No Braille detected. Please adjust the sheet.", interrupt=False)
                        _last_detected_state = detected
                except Exception as exc:
                    logger.debug("Presence detection error: %s", exc)
            time.sleep(0.7)  # Check every ~700ms

    def _preview_loop(self) -> None:
        """Continuously update live camera preview for sighted users/instructors."""
        while self._preview_running:
            if not self._is_scanning and getattr(self.app, "camera", None) and getattr(self.app, "display", None):
                frame = self.app.camera.capture_image()
                if frame is not None:
                    self._latest_frame = frame
                    if self.scanned_text:
                        status = "Translated! Press Enter to Read"
                    elif self._braille_detected is True:
                        status = "✓ Braille Detected! Press ENTER to Translate"
                    elif self._braille_detected is False:
                        status = "⚠ No Braille Detected - Adjust Sheet"
                    else:
                        status = "Position Braille inside box | Press Enter to Scan"
                    self.app.display.show_camera_preview(frame, status=status)
            time.sleep(0.18)  # ~5.5 fps viewfinder rate for smooth, tear-free SPI rendering

    def _scan_loop(self) -> None:
        """Capture and evaluate the Braille document."""
        if self.app.display:
            self.app.display.show_status("Scanning document with AI...")

        if not self.app.camera or not self.app.obr:
            if self.app.display:
                self.app.display.show_status("Hardware not configured.")
            if self.app.speech:
                self.app.speech.speak_text("Camera hardware not configured.", interrupt=True)
            self._is_scanning = False
            return

        image = self.app.camera.capture_image()
        if image is None:
            if self.app.display:
                self.app.display.show_status("Error: Could not capture image.")
            if self.app.speech:
                self.app.speech.speak_text("Error capturing image from camera.", interrupt=True)
            self._is_scanning = False
            return

        h, w = image.shape[:2]
        mx, my = int(w * 0.08), int(h * 0.08)
        cropped_image = image[my:h - my, mx:w - mx]
        result = self.app.obr.process_image(cropped_image)
        if not result.get("readable"):
            # Fallback to full uncropped frame
            result = self.app.obr.process_image(image)

        if result.get("readable") and result.get("text", "").strip():
            self.scanned_text = result.get("text").strip()
            self._is_scanning = False
            if self.app.display:
                self.app.display.show_status("Braille translated! Press Enter to Read.")
                self.app.display.show_text_buffer(self.scanned_text)
            if self.app.speech:
                self.app.speech.speak_text("Braille translated. Press Enter to hear it.", interrupt=False)
        else:
            self._is_scanning = False
            self._braille_detected = False
            err_msg = "No Braille Detected - Adjust Sheet"
            if self.app.display:
                self.app.display.show_status(f"⚠ {err_msg}")
            if self.app.speech:
                self.app.speech.speak_text("No Braille detected. Please adjust the sheet.", interrupt=True)

    def _speak_result(self) -> None:
        """Speak the text that was scanned upon user confirmation."""
        text = self.scanned_text
        self.scanned_text = None  # Reset for next scan
        self._braille_detected = None

        if self.app.display:
            self.app.display.show_status("Reading...")
            self.app.display.show_text_buffer(text)

        if self.app.speech and text:
            self.app.speech.speak_text(text, interrupt=False)

        if self.app.display:
            self.app.display.show_status("Position Braille inside box | Press Enter to Scan")

    def on_enter(self) -> None:
        logger.info("Entered Scanner Mode.")
        self.scanned_text = None
        self._is_scanning = False
        self._braille_detected = None
        self._latest_frame = None
        if self.app.display:
            self.app.display.clear()
            self.app.display.show_mode(self.mode_type)
            if hasattr(self.app.display, "show_scanner_viewfinder"):
                self.app.display.show_scanner_viewfinder()
            else:
                self.app.display.show_status("Position Braille inside box | Press Enter to Scan")

        # Start live camera viewfinder and detection loop
        self._preview_running = True
        self._preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self._preview_thread.start()
        self._detector_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self._detector_thread.start()

    def on_exit(self) -> None:
        logger.info("Exited Scanner Mode.")
        self._preview_running = False
        self._is_scanning = False
        self._braille_detected = None
        self._latest_frame = None
        if self.app.display:
            self.app.display.close_camera_preview()
