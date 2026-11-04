#!/usr/bin/env python3
"""
Brailce – Camera Module V2 & LCD Live Viewfinder Test
======================================================

Tests the Raspberry Pi Camera Module V2 with the 3.5" ILI9488 SPI LCD Screen.
- Displays live 25+ FPS camera feed on the LCD screen with green alignment box.
- Press [ENTER] to capture a frame and run YOLOv8 Optical Braille Recognition.
- Displays the decoded text on the LCD and speaks it aloud via Piper.
- Press [ESC] or [Q] to quit.

Usage:
    python tools/test_camera_lcd.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brailce.display.ili9488_display import ILI9488Display
from brailce.vision.camera import PiCameraDevice, SimulatedCamera
from brailce.vision.obr_engine import OBREngine
from brailce.config.loader import ConfigLoader
from brailce.speech.service import SpeechService


def main() -> None:
    print("=" * 65)
    print("  Brailce – Live Camera V2 & Optical Braille Reader Test")
    print("=" * 65)

    # 1. Initialize LCD Display
    print("\n[1/4] Initializing 3.5\" ILI9488 LCD...")
    display = ILI9488Display(width=480, height=320)
    display.initialize()
    print(f"      Display Driver: {display.driver_name} ({display._hardware_type.upper()})")

    # 2. Initialize Camera Module V2
    print("\n[2/4] Connecting to Raspberry Pi Camera Module V2...")
    cam = PiCameraDevice(resolution=(640, 480))
    is_real_camera = cam.is_available()
    if is_real_camera:
        print("      Camera Status: ONLINE (Hardware detected via Picamera2)!")
    else:
        err_msg = getattr(cam, "init_error", "Unknown initialization failure")
        print(f"      WARNING: Physical camera not detected!")
        print(f"      Diagnostic: {err_msg}")
        print("      Falling back to Simulated Camera.")
        cam = SimulatedCamera()

    # 3. Initialize YOLOv8 Braille Engine
    print("\n[3/4] Loading YOLOv8 Optical Braille Recognition Model...")
    model_path = os.path.join(str(PROJECT_ROOT), "brailce", "vision", "yolov8_braille.pt")
    obr = OBREngine(model_path=model_path)
    if obr._load_model():
        print("      YOLOv8 Model: READY (Loaded yolov8_braille.pt successfully)")
    else:
        print("      WARNING: Could not load YOLOv8 model.")

    # 4. Initialize the shared configured Piper speech engine.
    print("\n[4/4] Initializing Piper TTS engine...")
    speech = None
    try:
        config_path = PROJECT_ROOT / "brailce" / "config" / "config.json"
        speech = SpeechService.from_config(ConfigLoader.load(str(config_path)))
        print("      Speech: ONLINE")
    except Exception as exc:
        print(f"      Speech disabled or unavailable: {exc}")

    print("\n" + "=" * 65)
    if is_real_camera:
        print("  LIVE CAMERA V2 FEED IS STREAMING TO THE 3.5\" LCD!")
    else:
        print("  WARNING: SIMULATED CAMERA ACTIVE (Physical Camera Offline)")
    print("=" * 65)
    print("  Controls:")
    print("  • Look at the 3.5\" LCD screen: you should see the live camera feed!")
    print("  • Place Braille paper within the green alignment guide box.")
    print("  • Press [ENTER] in this terminal to scan and read the Braille.")
    print("  • Press [ESC] or [Q] to quit.")
    print("=" * 65 + "\n")

    running = True

    # Terminal non-blocking key reader
    import select
    import termios
    import tty

    fd = None
    old_settings = None
    if sys.platform != "win32":
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)

    try:
        last_frame_time = time.time()
        while running:
            # Grab camera frame
            frame = cam.capture_image()
            if frame is not None:
                if not is_real_camera:
                    status = "⚠ NO CAMERA DETECTED | Check Cable Connection"
                else:
                    status = "Position Braille in box | Press ENTER to Scan"
                display.show_camera_preview(
                    frame,
                    status=status
                )

            # Check keyboard input with 65ms frame pacing (~15 FPS to avoid SPI tearing)
            key_pressed = None
            if sys.platform != "win32":
                r, _, _ = select.select([sys.stdin], [], [], 0.065)
                if r:
                    key_pressed = sys.stdin.read(1)
            else:
                import msvcrt
                if msvcrt.kbhit():
                    key_pressed = msvcrt.getch().decode("utf-8", errors="ignore")
                time.sleep(0.065)

            if key_pressed in ("\x1b", "q", "Q", "\x03"):  # ESC / Q / Ctrl+C
                print("\nExiting camera test...")
                break

            elif key_pressed in ("\r", "\n"):  # ENTER -> Scan!
                print("\n[SCAN TRIGGERED] Capturing high-res frame...")
                scan_frame = cam.capture_image()
                if scan_frame is None:
                    print("Error: Could not capture frame for scanning.")
                    continue

                # Crop to active green guide box region (exclude outside clutter/handwriting)
                h, w = scan_frame.shape[:2]
                mx, my = int(w * 0.12), int(h * 0.12)
                cropped_frame = scan_frame[my:h - my, mx:w - mx]

                display.show_status("AI Scanning: Detecting Braille cells...")
                print("[AI Scanning] Running YOLOv8 detection...")

                t0 = time.time()
                result = obr.process_image(cropped_frame)
                dt = time.time() - t0

                if result.get("readable"):
                    text = result.get("text", "")
                    print(f"\n" + "=" * 50)
                    print(f"  SUCCESS! Scanned in {dt:.2f}s:")
                    print(f"  Result: {text}")
                    print("=" * 50 + "\n")

                    display.show_status(f"Read: {text[:40]}")
                    if speech:
                        speech.speak(f"Scanned document says: {text}")
                else:
                    err = result.get("text", "Not readable. Adjust lighting/distance.")
                    print(f"\n[Scan Notice]: {err}\n")
                    display.show_status(err)
                    if speech:
                        speech.speak("Not enough Braille detected. Please adjust camera.")

                # Pause 2 seconds so user can see result on LCD
                time.sleep(2.0)

    finally:
        if fd is not None and old_settings is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        cam.close()
        if speech:
            speech.shutdown()
        display.clear()
        display.show_status("Camera Test Completed.")
        print("Camera test ended cleanly.")


if __name__ == "__main__":
    main()
