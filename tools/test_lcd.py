#!/usr/bin/env python3
"""
Brailce – LCD Screen Hardware Diagnostic & Visual Test Tool
=============================================================

Tests the 3.5-inch 480x320 TFT LCD screen on Raspberry Pi (or simulation on PC).

What this script does:
1. Detects Linux framebuffer device (/dev/fb1 for SPI TFT or /dev/fb0 for HDMI).
2. Renders all 4 Brailce operating modes (Free Input, Math, AI, Scanner).
3. Renders character cards, Braille dot matrices, and camera alignment guides.
4. Flushes directly to the hardware display so you can see it physically.
5. Saves 'lcd_test_output.png' so you can visually verify the rendering.

Usage:
    python tools/test_lcd.py
    python tools/test_lcd.py --fb /dev/fb1
    python tools/test_lcd.py --save-only
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brailce.core.events import AppMode
from brailce.display.ili9488_display import ILI9488Display


def check_raspberry_pi_environment() -> dict:
    """Inspect system to see what display devices are present."""
    info = {
        "is_raspberry_pi": False,
        "fb0_exists": os.path.exists("/dev/fb0"),
        "fb1_exists": os.path.exists("/dev/fb1"),
        "spi_enabled": os.path.exists("/dev/spidev0.0"),
    }

    # Check for Raspberry Pi model string in device tree
    model_path = "/proc/device-tree/model"
    if os.path.exists(model_path):
        try:
            with open(model_path, "r") as f:
                model = f.read().strip().replace("\x00", "")
                info["is_raspberry_pi"] = "Raspberry Pi" in model
                info["model"] = model
        except Exception:
            pass

    return info


def run_lcd_test(fb_path: str = None, pause: float = 2.0) -> None:
    print("=" * 60)
    print("  Brailce – 3.5\" TFT LCD Display Hardware Diagnostic")
    print("=" * 60)

    env = check_raspberry_pi_environment()
    if env["is_raspberry_pi"]:
        print(f"Hardware Detected: {env.get('model', 'Raspberry Pi')}")
        print(f"SPI Interface    : {'Active (/dev/spidev0.0)' if env['spi_enabled'] else 'Not detected'}")
        print(f"Framebuffer fb1  : {'Found (/dev/fb1)' if env['fb1_exists'] else 'Not present (Normal on Pi 5 / Bookworm)'}")
        print(f"Framebuffer fb0  : {'Found (/dev/fb0 - HDMI)' if env['fb0_exists'] else 'Not active'}")
    else:
        print("Running in Host Simulation Mode (PC / Mac / Headless).")

    print("-" * 60)

    # Initialize display
    display = ILI9488Display(width=480, height=320, fb_path=fb_path)
    display.initialize()

    print(f"Driver Active     : {display.driver_name}")
    print(f"Hardware Link     : {display._hardware_type.upper()}")
    if display._hardware_type == "canvas" and display._init_error:
        print(f"SPI Hardware Error: {display._init_error}")
    print("\nStarting screen visual test sequence...\n")

    # ---- Step 1: Free Input Mode ----
    print("[1/4] Rendering FREE INPUT MODE UI...")
    display.clear()
    display.show_mode(AppMode.FREE_INPUT)
    display.show_character("A")
    display.show_braille("⠁", "Dot 1", "●○\n○○\n○○")
    display.show_text_buffer("HELLO WORLD")
    display.show_status("Ready — press any key")
    display.save_screenshot("lcd_test_free_input.png")
    time.sleep(pause)

    # ---- Step 2: Math Mode ----
    print("[2/4] Rendering MATH MODE UI (Grade 1 DepEd Solution Card)...")
    display.clear()
    display.show_mode(AppMode.MATH)
    display.show_math_result(
        equation="5 + 3",
        result="8",
        explanation="Start at 5, and count up 3 more: 6, 7, 8. The answer is 8.",
        short_step="Start 5 -> 6, 7, 8"
    )
    display.show_status("Ready for math. Press digits and operators.")
    display.save_screenshot("lcd_test_math_mode.png")
    time.sleep(pause)

    # ---- Step 3: AI Assistant Mode ----
    print("[3/4] Rendering AI ASSISTANT MODE UI (Single-digit Math Query)...")
    display.clear()
    display.show_mode(AppMode.AI_ASSISTANT)
    display.show_ai_response("Two plus two equals four. In Brailce, math is single digits (0-9).", query="WHAT IS 2 + 2?")
    display.show_status("AI response ready.")
    display.save_screenshot("lcd_test_ai_mode.png")
    time.sleep(pause)

    # ---- Step 4: Scanner Mode Viewfinder ----
    print("[4/4] Rendering SCANNER MODE (Camera Viewfinder with Alignment Guides)...")
    display.clear()
    display.show_mode(AppMode.SCANNER)
    display.show_scanner_viewfinder(status="Position Braille inside box | Press Enter to Scan")
    display.save_screenshot("lcd_test_scanner_mode.png")
    time.sleep(pause)

    # Restore to Free Input Mode
    display.clear()
    display.show_mode(AppMode.FREE_INPUT)
    display.show_status("Brailce System Ready")
    display.save_screenshot("lcd_test_output.png")

    print("\n" + "=" * 60)
    print("  TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("Screenshots saved:")
    print("  • lcd_test_free_input.png  (Free Input Mode card)")
    print("  • lcd_test_math_mode.png   (Math Mode solution card)")
    print("  • lcd_test_ai_mode.png     (AI Assistant Mode card)")
    print("  • lcd_test_scanner_mode.png(Scanner live camera viewfinder)")
    print("  • lcd_test_output.png      (Final screen state)")
    print("\nScreen is now live! Press Ctrl+C in terminal when finished viewing.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting LCD test...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Brailce 3.5\" TFT LCD display.")
    parser.add_argument("--fb", type=str, default=None, help="Framebuffer device path (e.g. /dev/fb1 or /dev/fb0)")
    parser.add_argument("--pause", type=float, default=2.0, help="Pause seconds between test cards (default: 2.0)")
    args = parser.parse_args()

    run_lcd_test(fb_path=args.fb, pause=args.pause)
