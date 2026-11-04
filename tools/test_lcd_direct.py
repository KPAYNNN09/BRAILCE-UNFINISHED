#!/usr/bin/env python3
"""
Direct LCD Test Script for Raspberry Pi 5 + 3.5" TFT SPI Display.
Bypasses RPi.GPIO and disables backlight pin 18 (which is reserved by MAX98357A I2S audio).
"""

import sys
import time

def run_test() -> None:
    print("=" * 60)
    print("BRAILCE DIRECT HARDWARE LCD TEST (Raspberry Pi 5)")
    print("=" * 60)

    try:
        import lgpio
        from PIL import Image, ImageDraw
        from luma.core.interface.serial import spi
        import luma.lcd.device as devices
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please run within the virtual environment:")
        print("  ~/brailce/venv/bin/python3 tools/test_lcd_direct.py")
        sys.exit(1)


class LgpioShim:
    """RP1 gpiochip4 shim for luma.core on Raspberry Pi 5."""
    OUT = 1
    IN = 0
    HIGH = 1
    LOW = 0
    BCM = 11
    BOARD = 10

    def __init__(self, chip: int = 4):
        self._lgpio = lgpio
        try:
            self._h = lgpio.gpiochip_open(chip)
            print(f"[OK] Opened GPIO chip {chip} (RP1)")
        except Exception as e:
            print(f"[WARN] Failed to open chip {chip}: {e}, falling back to chip 0")
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

    def cleanup(self, pin=None) -> None:
        pass


class NoopBacklight:
    def __call__(self, val=True): pass
    def cleanup(self): pass


    shim = LgpioShim(chip=4)

    drivers = ["ili9488", "ili9486"]
    success = False

    for drv_name in drivers:
        if not hasattr(devices, drv_name):
            continue

        print(f"\n--> Testing driver: {drv_name.upper()}...")
        try:
            # Re-initialize SPI with DC=24, RST=25
            serial = spi(
                port=0,
                device=0,
                gpio_DC=24,
                gpio_RST=25,
                bus_speed_hz=8000000,
                gpio=shim,
            )

            cls = getattr(devices, drv_name)
            # CRITICAL: backlight=NoopBacklight() prevents luma from claiming GPIO 18 (used by I2S audio)
            dev = cls(
                serial,
                width=480,
                height=320,
                rotate=0,
                gpio=shim,
                backlight=NoopBacklight(),
            )

            # Draw a bright test pattern matching device dimensions
            img = Image.new("RGB", (dev.width, dev.height), color=(180, 0, 0))
            draw = ImageDraw.Draw(img)
            # Draw green border
            draw.rectangle([5, 5, dev.width - 6, dev.height - 6], outline=(0, 255, 0), width=4)
            draw.text((60, 100), "BRAILCE LCD HARDWARE TEST", fill=(255, 255, 255))
            draw.text((60, 140), f"DRIVER: {drv_name.upper()}", fill=(255, 255, 0))
            draw.text((60, 180), "SUCCESS! SCREEN IS CONNECTED & WORKING!", fill=(0, 255, 255))
            draw.text((60, 220), "Holding for 10 seconds...", fill=(200, 200, 200))

            dev.display(img)
            print(f">>> SUCCESS! Sent frame using driver: {drv_name.upper()}!")
            print(">>> LOOK AT YOUR LCD SCREEN NOW! (Holding for 10s...)")
            time.sleep(10)
            success = True
            break
        except Exception as e:
            print(f"    Driver {drv_name} failed: {e}")

    if not success:
        print("\n[ERROR] Neither driver succeeded. Check SPI pins or wiring.")
    else:
        print("\n[DONE] LCD Direct Test complete!")


if __name__ == "__main__":
    run_test()
