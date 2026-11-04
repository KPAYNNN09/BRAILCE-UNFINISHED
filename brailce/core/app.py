"""
Brailce – Main Application Controller
========================================

Orchestrates the entire application lifecycle:
    1. Load configuration
    2. Initialize subsystems (input, display, speech, power)
    3. Run system checks
    4. Start the event loop
    5. Route events to the active mode
    6. Handle shutdown gracefully

This is the top-level coordinator — it does not contain
business logic itself, only wiring and lifecycle management.
"""

from __future__ import annotations

import logging
import signal
import sys
from typing import Optional

from brailce.config.loader import ConfigLoader
from brailce.core.events import AppMode, EventType, InputEvent
from brailce.core.mode_manager import ModeManager
from brailce.core.state import ApplicationState
from brailce.display.base import DisplayDevice
from brailce.display.console_display import ConsoleDisplay
from brailce.input.base import InputDevice
from brailce.input.keyboard_input import KeyboardInputDevice
from brailce.braille.mapping import BrailleMappingService
from brailce.braille.encoder import BrailleEncoder
from brailce.modes.ai_assistant import AIAssistantMode
from brailce.modes.base_mode import BaseMode
from brailce.modes.free_input import FreeInputMode
from brailce.modes.math_mode import MathMode
from brailce.modes.scanner_mode import ScannerMode
from brailce.power.base import PowerMonitor
from brailce.power.simulated import SimulatedPowerMonitor
from brailce.speech.base import SpeechEngine
from brailce.speech.service import SpeechService
from brailce.utils.system_checks import run_all_checks
from brailce.vision.camera import CameraDevice, SimulatedCamera, PiCameraDevice
from brailce.vision.obr_engine import OBREngine

logger = logging.getLogger(__name__)


class BrailceApp:
    """
    Main application controller for the Brailce system.

    Manages the lifecycle of all subsystems and routes input events
    to the currently active application mode.
    """

    def __init__(self, config: ConfigLoader) -> None:
        self.config = config
        self.state = ApplicationState()
        self.mode_manager = ModeManager(self.state)

        # Subsystems (initialized in setup())
        self.input_device: Optional[InputDevice] = None
        self.display: Optional[DisplayDevice] = None
        self.speech: Optional[SpeechEngine] = None
        self.sound = None
        self.power: Optional[PowerMonitor] = None
        self.camera: Optional[CameraDevice] = None
        self.obr: Optional[OBREngine] = None
        self.mapping_service: Optional[BrailleMappingService] = None
        self.encoder: Optional[BrailleEncoder] = None
        
        # We can't import OllamaClient at top level to avoid circular issues or keep it optional,
        # so we just use Any or type string for it if needed, but since we didn't import it at top,
        # we'll just declare it here.
        self.ai_client = None

        # Mode instances
        self._modes: dict[AppMode, BaseMode] = {}
        self._active_mode: Optional[BaseMode] = None

    # ---- Lifecycle ----

    def setup(self) -> None:
        """Initialize all subsystems based on configuration."""
        logger.info("Brailce application setup starting...")

        # ---- Input Device ----
        device_type = self.config.input_device
        if device_type == "keyboard":
            self.input_device = KeyboardInputDevice(
                mode_getter=lambda: self.state.mode
            )
        else:
            logger.warning(
                "Input device '%s' not available — "
                "falling back to keyboard simulation.",
                device_type,
            )
            self.input_device = KeyboardInputDevice(
                mode_getter=lambda: self.state.mode
            )

        self.input_device.register_callback(self._on_input_event)

        # ---- Display ----
        display_driver = self.config.display_driver
        if display_driver == "auto":
            import os
            # On Raspberry Pi with SPI TFT or framebuffer, automatically use ILI9488 TFT; otherwise Console
            if os.path.exists("/dev/spidev0.0") or os.path.exists("/dev/fb1") or (os.path.exists("/dev/fb0") and os.path.exists("/proc/device-tree/model")):
                from brailce.display.ili9488_display import ILI9488Display
                width = self.config.get("display", "width", default=480)
                height = self.config.get("display", "height", default=320)
                self.display = ILI9488Display(width=width, height=height)
            else:
                self.display = ConsoleDisplay()
        elif display_driver == "ili9488":
            from brailce.display.ili9488_display import ILI9488Display
            width = self.config.get("display", "width", default=480)
            height = self.config.get("display", "height", default=320)
            self.display = ILI9488Display(width=width, height=height)
        else:
            self.display = ConsoleDisplay()

        self.display.initialize()

        # ---- Speech ----
        if self.config.speech_enabled:
            self.speech = SpeechService.from_config(self.config)
            logger.info("Speech: initialized %s.", self.speech.engine_name)
        else:
            self.speech = None
            logger.info("Speech is disabled in configuration.")

        # ---- Sound Effects ----
        from brailce.audio.sound_effects import SoundEffectsEngine
        sound_enabled = self.config.get("sound", "enabled", default=False)
        sound_vol = self.config.get("sound", "volume", default=0)
        self.sound = SoundEffectsEngine(enabled=sound_enabled, volume=sound_vol)
            
        # ---- AI ----
        if self.config.ai_enabled:
            ai_cfg = self.config.section("ai")
            from brailce.ai.ollama_client import OllamaClient
            self.ai_client = OllamaClient(
                host=ai_cfg.get("host", "http://127.0.0.1:11434"),
                model=ai_cfg.get("model", "liquidai/lfm2.5-1.2b-instruct"),
                system_prompt=ai_cfg.get("system_prompt", None),
                num_predict=ai_cfg.get("max_response_tokens", 50),
            )
        else:
            self.ai_client = None

        # ---- Power ----
        import sys
        if sys.platform != "win32":
            from brailce.power.rpi_power import PiPowerMonitor
            self.power = PiPowerMonitor()
        else:
            self.power = SimulatedPowerMonitor()

        if hasattr(self.display, "set_power_monitor"):
            self.display.set_power_monitor(self.power)
        
        # ---- Vision ----
        vision_driver = self.config.get("vision", "driver", default="auto")
        if vision_driver == "simulated":
            test_image = self.config.get("vision", "test_image_path", default="")
            self.camera = SimulatedCamera(image_path=test_image if test_image else None)
        elif vision_driver == "picamera":
            self.camera = PiCameraDevice()
        else:  # auto
            pi_cam = PiCameraDevice()
            if pi_cam.is_available():
                self.camera = pi_cam
                logger.info("Using physical Raspberry Pi Camera Module.")
            else:
                test_image = self.config.get("vision", "test_image_path", default="")
                self.camera = SimulatedCamera(image_path=test_image if test_image else None)
                logger.info("Physical camera not active — using SimulatedCamera fallback.")
            
        model_path = self.config.get("vision", "model_path", default="brailce/vision/yolov8_braille.pt")
        conf = float(self.config.get("vision", "confidence_threshold", default=0.22))
        iou = float(self.config.get("vision", "iou_threshold", default=0.45))
        self.obr = OBREngine(model_path=model_path, conf=conf, iou=iou)

        # ---- Braille Mapping ----
        self.mapping_service = BrailleMappingService()
        self.mapping_service.load_from_config(self.config)
        self.encoder = BrailleEncoder(self.mapping_service)

        # ---- Modes ----
        self._modes[AppMode.FREE_INPUT] = FreeInputMode(self)
        self._modes[AppMode.MATH] = MathMode(self)
        self._modes[AppMode.AI_ASSISTANT] = AIAssistantMode(self)
        self._modes[AppMode.SCANNER] = ScannerMode(self)
        self._active_mode = self._modes[AppMode.FREE_INPUT]
        self._active_mode.on_enter()

        # Register mode-change listener
        self.mode_manager.register_listener(self._on_mode_change)

        # ---- System Checks ----
        ai_host = self.config.get("ai", "host", default="http://127.0.0.1:11434")
        piper_model_path = self.config.get(
            "speech", "model_path", default="~/piper/en_US-ryan-medium.onnx"
        )
        checks = run_all_checks(
            ollama_host=ai_host,
            piper_model_path=piper_model_path,
        )
        for check in checks:
            if not check.available:
                self.display.show_status(f"⚠ {check.name}: {check.message}")

        # ---- Display Initial State ----
        self.display.show_mode(self.state.mode)
        self.display.show_text_buffer(self.state.text_buffer)

        # Initial speech announcement so learner knows device is ready
        if self.speech:
            self.speech.speak_text("Free Input Mode. Ready to type.", interrupt=False)

        logger.info("Brailce application setup complete.")
        logger.info(
            "Input: %s | Display: %s | Speech: %s",
            self.input_device.device_name,
            self.display.driver_name,
            self.speech.engine_name if self.speech else "Disabled",
        )

    def run(self) -> None:
        """Start the main event loop."""
        if self.input_device is None:
            raise RuntimeError("Call setup() before run().")

        logger.info("Brailce application starting...")
        self.display.show_status("Ready — press any character key.")

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            self.input_device.start()

            # Keep main thread alive while input runs in background
            while self.state.is_running:
                try:
                    import time
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    break

        except Exception as exc:
            logger.exception("Fatal error in main loop: %s", exc)
            if self.display:
                self.display.show_error(f"Fatal error: {exc}")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shut down all subsystems."""
        logger.info("Brailce shutting down...")
        self.state.is_running = False

        if self.input_device:
            try:
                self.input_device.stop()
            except Exception:
                logger.exception("Error stopping input device.")

        if self.speech:
            try:
                if hasattr(self.speech, 'shutdown'):
                    self.speech.shutdown()
                else:
                    self.speech.stop()
            except Exception:
                logger.exception("Error stopping speech engine.")

        if self.display:
            try:
                self.display.show_status("Shutting down...")
                self.display.shutdown()
            except Exception:
                logger.exception("Error shutting down display.")

        if self.camera and hasattr(self.camera, "close"):
            try:
                self.camera.close()
            except Exception:
                logger.exception("Error stopping camera device.")

        logger.info("Brailce shutdown complete.")

    # ---- Event Handling ----

    def _on_input_event(self, event: InputEvent) -> None:
        """
        Central event router.

        Dispatches input events to the appropriate handler
        based on event type and current mode.
        """
        logger.debug("Event received: %s", event)

        # ---- System-level events ----
        if event.event_type == EventType.QUIT:
            logger.info("Quit event received.")
            self.state.is_running = False
            return

        if event.event_type == EventType.MODE_PRESSED:
            self.mode_manager.toggle()
            return

        if event.event_type == EventType.VOLUME_UP:
            new_vol = self.state.increase_volume()
            if self.display:
                self.display.show_status(f"Volume: {new_vol}")
            if self.speech:
                self.speech.set_volume(new_vol)
                self.speech.speak_text(f"Volume {new_vol} percent", interrupt=True)
            return

        if event.event_type == EventType.VOLUME_DOWN:
            new_vol = self.state.decrease_volume()
            if self.display:
                self.display.show_status(f"Volume: {new_vol}")
            if self.speech:
                self.speech.set_volume(new_vol)
                self.speech.speak_text(f"Volume {new_vol} percent", interrupt=True)
            return

        # ---- Mode-specific events ----
        if self._active_mode:
            self._active_mode.handle_event(event)

    def _on_mode_change(self, old_mode: AppMode, new_mode: AppMode) -> None:
        """Handle mode transitions."""
        # 1. Immediately stop any in-flight speech from the previous mode
        if self.speech:
            try:
                self.speech.stop()
            except Exception:
                pass

        # 2. Reset display state to prevent cross-mode pollution
        if self.display:
            if hasattr(self.display, "_current_query"):
                self.display._current_query = ""

        # Exit old mode
        old_mode_instance = self._modes.get(old_mode)
        if old_mode_instance:
            old_mode_instance.on_exit()

        # Enter new mode
        new_mode_instance = self._modes.get(new_mode)
        if new_mode_instance:
            new_mode_instance.on_enter()
            self._active_mode = new_mode_instance

        # Update display
        if self.display:
            self.display.show_mode(new_mode)

        # Announce mode changes through the shared Piper speech pipeline.
        if self.speech:
            mode_announcements = {
                AppMode.FREE_INPUT: "Free Input Mode.",
                AppMode.MATH: "Math Mode.",
                AppMode.AI_ASSISTANT: "AI Assistant Mode.",
                AppMode.SCANNER: "Scanner Mode.",
            }
            announcement = mode_announcements.get(new_mode, f"{new_mode.display_name()}.")
            self.speech.speak_text(announcement, interrupt=False)

        logger.info("Mode changed to: %s", new_mode.display_name())

    def _signal_handler(self, signum: int, frame: object) -> None:
        """Handle interrupt signals gracefully."""
        logger.info("Signal %d received — shutting down.", signum)
        self.state.is_running = False
