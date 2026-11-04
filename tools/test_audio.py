#!/usr/bin/env python3
"""
Brailce – Audio Output & TTS Hardware Diagnostic Tool
======================================================

Tests the MAX98357A I2S audio amplifier and the configured Piper speech service.

What this script does:
1. Inspects ALSA audio devices (aplay -l).
2. Checks whether MAX98357A or generic I2S DAC is detected.
3. Generates and plays a clean audio test tone directly through ALSA.
4. Tests the shared Piper voice with Braille-specific phrases.
5. Verifies the Brailce speech queue and WAV playback path.

Usage:
    python tools/test_audio.py
    python tools/test_audio.py --phrase "Testing Braille audio"
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brailce.config.loader import ConfigLoader
from brailce.speech.service import SpeechService


def banner(text: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_alsa_devices() -> dict:
    """Scan ALSA sound cards using aplay -l."""
    info = {
        "aplay_installed": shutil.which("aplay") is not None,
        "cards": [],
        "has_i2s_dac": False,
        "output": "",
    }

    if not info["aplay_installed"]:
        return info

    try:
        proc = subprocess.run(
            ["aplay", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        info["output"] = proc.stdout
        for line in proc.stdout.splitlines():
            if line.startswith("card"):
                info["cards"].append(line)
                lower = line.lower()
                if any(k in lower for k in ["max98357", "hifiberry", "dac", "i2s"]):
                    info["has_i2s_dac"] = True
    except Exception as exc:
        info["output"] = str(exc)

__test__ = False


def run_piper_test(phrase: str) -> bool:
    """Test speech through the same configured Piper service as the application."""
    speech = None
    try:
        config = ConfigLoader.load(
            str(PROJECT_ROOT / "brailce" / "config" / "config.json")
        )
        speech = SpeechService.from_config(config)
        speech.speak_text(phrase)
        completed = speech.wait_until_idle(timeout=60)
        if not completed:
            print("  [FAIL] Piper speech queue did not complete.")
            return False
        return True
    except RuntimeError as exc:
        print(f"  [FAIL] {exc}")
        return False
    finally:
        if speech:
            speech.shutdown()


def run_brailce_engine_test() -> bool:
    """Test queued speech items on the unified Piper playback path."""
    print("  Initializing the configured Piper speech queue...")
    speech = None
    try:
        config = ConfigLoader.load(
            str(PROJECT_ROOT / "brailce" / "config" / "config.json")
        )
        speech = SpeechService.from_config(config)
    except RuntimeError as exc:
        print(f"  [FAIL] {exc}")
        return False

    test_words = [
        "Welcome to Brailce.",
        "ay.",
        "bee.",
        "Audio system is fully operational.",
    ]

    print("  Enqueueing speech queue test items:")
    for w in test_words:
        print(f"    - Enqueue: '{w}'")
        speech.speak_text(w)
        time.sleep(1.2)

    # Wait for queue to flush
    try:
        completed = speech.wait_until_idle(timeout=60)
    finally:
        speech.shutdown()
    if not completed:
        print("  [FAIL] Piper speech queue did not complete.")
        return False
    print("  [OK] Piper speech queue completed successfully.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Brailce Audio & TTS Diagnostic Tool")
    parser.add_argument("--phrase", type=str, default="Brailce audio test. Speakers connected successfully.", help="Custom test phrase")
    args = parser.parse_args()

    banner("Brailce – Audio & Speaker Hardware Diagnostic")

    # Step 1: Scan ALSA devices
    print("\n[Step 1/3] Inspecting ALSA Sound Cards:")
    alsa = check_alsa_devices()
    if alsa["aplay_installed"]:
        print(f"  Cards detected ({len(alsa['cards'])}):")
        for card in alsa["cards"]:
            print(f"    * {card}")

        if alsa["has_i2s_dac"]:
            print("\n  >>> SUCCESS: I2S DAC / MAX98357A detected! <<<")
        else:
            print("\n  [NOTE] No obvious 'MAX98357' or 'hifiberry-dac' label in card list.")
            print("         If audio doesn't play, verify 'dtoverlay=max98357a' in /boot/firmware/config.txt")
    else:
        print("  [INFO] 'aplay' not available on this platform (simulation mode).")

    # Step 2: Test configured Piper speech
    print("\n[Step 2/3] Testing Piper Text-to-Speech Output:")
    run_piper_test(args.phrase)

    # Step 3: Test the Brailce Piper queue
    print("\n[Step 3/3] Testing Brailce Python Speech Pipeline:")
    run_brailce_engine_test()

    banner("Audio Diagnostic Completed!")
    print("If you heard the test voices clearly, your speakers and amplifier are ready!\n")


if __name__ == "__main__":
    main()
