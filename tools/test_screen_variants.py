#!/usr/bin/env python3
"""
Brailce – LCD Screen Controller Auto-Detection Diagnostic
==========================================================
Tests the 3.5" TFT display against common controller variants:
1. ILI9486 (at 8MHz, 4MHz, 16MHz)
2. ILI9488 (at 8MHz, 4MHz, 16MHz)
3. ST7796  (if supported)

Fills the screen with distinct solid colors (Red -> Green -> Blue -> Brailce Card)
so you can immediately see when the screen initializes!
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def run_diagnostics():
    print("=" * 60)
    print("  Brailce – 3.5\" TFT Display Multi-Controller Diagnostic")
    print("=" * 60)

    try:
        from luma.core.interface.serial import spi
        from luma.core.render import canvas
        import luma.lcd.device as devices
        from PIL import Image, ImageDraw
    except ImportError as e:
        print(f"Error importing libraries: {e}")
        return

    # Check available drivers in luma.lcd
    available = [d for d in ["ili9488", "ili9486", "st7796", "ili9341"] if hasattr(devices, d)]
    print(f"Supported drivers in luma.lcd: {available}")

    # BCM Pin configuration (Physical Pin 18 = GPIO 24, Pin 22 = GPIO 25, Pin 24 = CE0)
    gpio_dc = 24
    gpio_rst = 25

    print(f"\nUsing Pin Mapping: DC=GPIO{gpio_dc} (Pin 18), RST=GPIO{gpio_rst} (Pin 22), CS=CE0 (Pin 24)")
    print("-" * 60)

    # Reset pin locks on Raspberry Pi 5
    import os
    os.system("pinctrl set 24,25 ip 2>/dev/null")

    class GpioZeroShim:
        OUT = 1; HIGH = 1; LOW = 0
        def __init__(self): self._devices = {}
        def setmode(self, mode): pass
        def setup(self, pin, mode):
            import gpiozero
            if pin not in self._devices:
                self._devices[pin] = gpiozero.OutputDevice(pin, initial_value=False)
        def output(self, pin, value):
            dev = self._devices.get(pin)
            if dev: dev.on() if value else dev.off()
        def cleanup(self, pin=None):
            for dev in list(self._devices.values()): dev.close()
            self._devices.clear()

    test_configs = []
    for driver_name in ["ili9486", "ili9488"]:
        if hasattr(devices, driver_name):
            for speed in [16000000, 8000000, 4000000]:
                test_configs.append((driver_name, speed))

    for driver_name, speed_hz in test_configs:
        speed_mhz = speed_hz / 1_000_000
        print(f"\n>>> Trying driver [{driver_name.upper()}] at {speed_mhz:.0f} MHz SPI clock...")
        try:
            os.system("pinctrl set 24,25 ip 2>/dev/null")
            driver_cls = getattr(devices, driver_name)
            gpio_shim = GpioZeroShim()
            serial = spi(
                port=0,
                device=0,
                gpio_DC=gpio_dc,
                gpio_RST=gpio_rst,
                bus_speed_hz=speed_hz,
                gpio=gpio_shim,
            )
            device = driver_cls(serial, width=480, height=320, rotate=1)

            # Test 1: Fill RED
            img_red = Image.new("RGB", (480, 320), color=(255, 0, 0))
            draw = ImageDraw.Draw(img_red)
            draw.text((40, 140), f"TEST OK: {driver_name.upper()} @ {speed_mhz:.0f}MHz", fill=(255, 255, 255))
            device.display(img_red)
            print(f"    Sent RED test frame. Did the screen turn RED? (Waiting 3s...)")
            time.sleep(3)

            # Test 2: Fill BLUE
            img_blue = Image.new("RGB", (480, 320), color=(10, 40, 120))
            draw = ImageDraw.Draw(img_blue)
            draw.text((40, 140), f"BRAILCE READY! ({driver_name.upper()})", fill=(255, 255, 255))
            device.display(img_blue)
            print(f"    Sent BLUE test frame.")
            time.sleep(2)

            device.cleanup()
        except Exception as exc:
            print(f"    Failed with {driver_name}: {exc}")

    print("\n" + "=" * 60)
    print("Diagnostic cycle finished.")
    print("If the screen stayed white during all tests:")
    print("1. Unplug any Touch pins (T_CLK, T_CS, T_DIN) and SDO(MISO).")
    print("2. Verify GPIO 24 (Pin 18) and GPIO 25 (Pin 22).")
    print("=" * 60)

if __name__ == "__main__":
    run_diagnostics()
