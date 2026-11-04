#!/usr/bin/env python3
"""
Brailce – AI Mode Direct LCD Screen Interactive Test
======================================================

Directly launches AI Assistant Mode on the physical 3.5" ILI9488 LCD screen
powered by offline Liquid AI (liquidai/lfm2.5-1.2b-instruct) via Ollama.

Features:
- Initializes ILI9488 SPI LCD directly
- Connects to Ollama (liquidai/lfm2.5-1.2b-instruct)
- Live typing: letters appear immediately on the LCD query card with yellow cursor
- Press ENTER: triggers "⚡ LIQUID AI IS THINKING..." purple card, queries Ollama,
  renders multi-line answer on LCD, and speaks via the shared Piper service.
- Quick test hotkeys:
  [1] Ask "What is Braille?"
  [2] Ask "What is 15 + 27?"
  [3] Ask "Explain the shape of my heart."
  [ESC] Exit

Usage on Raspberry Pi:
    python tools/test_ai_lcd.py
"""

from __future__ import annotations

import os
import sys
import time
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brailce.core.events import AppMode
from brailce.display.ili9488_display import ILI9488Display
from brailce.ai.ollama_client import OllamaClient
from brailce.config.loader import ConfigLoader
from brailce.speech.service import SpeechService
from brailce.utils.validation import validate_ai_query


def main() -> None:
    print("=" * 65)
    print("  Brailce – Direct AI Assistant Mode on 3.5\" TFT LCD")
    print("=" * 65)

    # 1. Initialize Display
    print("\n[1/3] Initializing ILI9488 3.5\" LCD Screen...")
    display = ILI9488Display(width=480, height=320)
    display.initialize()
    print(f"      Driver: {display.driver_name} ({display._hardware_type.upper()})")

    # 2. Initialize Ollama
    ai_model = "liquidai/lfm2.5-1.2b-instruct"
    system_prompt = (
        "You are Brailce, an emotional, encouraging, and highly logical educational AI "
        "for a Braille learning device. CRITICAL RULE FOR MATH: All math-related questions "
        "must be single digits only (numbers 0 to 9, e.g. 2 + 2, 5 + 3). If any math question "
        "involves numbers greater than 9, politely state: 'In Brailce, math questions are for "
        "single digits only, from 0 to 9.' Keep answers concise (under 2 short sentences). "
        "Do not use markdown formatting."
    )
    print(f"\n[2/3] Connecting to Ollama with model: {ai_model}...")
    ai = OllamaClient(
        host="http://127.0.0.1:11434",
        model=ai_model,
        system_prompt=system_prompt,
    )
    if ai.is_available():
        print("      Ollama Service: ONLINE (127.0.0.1:11434)")
    else:
        print("      WARNING: Ollama service did not respond to /api/tags.")
        print("      Make sure 'ollama serve' is active.")

    # 3. Initialize the same configured speech service used by the app.
    print("\n[3/3] Initializing Piper speech engine...")
    speech = None
    try:
        config_path = PROJECT_ROOT / "brailce" / "config" / "config.json"
        speech = SpeechService.from_config(ConfigLoader.load(str(config_path)))
        print("      Speech: ONLINE")
    except Exception as exc:
        print(f"      Speech disabled or unavailable: {exc}")

    # Set Display to AI Assistant Mode
    display.clear()
    display.show_mode(AppMode.AI_ASSISTANT)
    display.show_ai_query_input("")
    display.save_screenshot("ai_lcd_ready.png")

    print("\n" + "=" * 65)
    print("  AI ASSISTANT IS LIVE ON THE LCD SCREEN!")
    print("=" * 65)
    print("  Controls:")
    print("  • Type characters from your keyboard (appear live on screen)")
    print("  • Press [ENTER] to ask Liquid AI")
    print("  • Press [BACKSPACE] to delete character")
    print("  • Quick Hotkeys:")
    print("      [1] Ask 'What is Braille?'")
    print("      [2] Ask 'What is 5 + 3?' (Single-digit math allowed)")
    print("      [3] Ask 'Explain the shape of my heart.'")
    print("      [4] Test Multi-digit Math: 'What is 15 + 27?' (Restriction test)")
    print("  • Press [ESC] or [Ctrl+C] to quit")
    print("=" * 65 + "\n")

    query_buffer = ""
    is_processing = False

    def ask_ai(prompt_text: str) -> None:
        nonlocal is_processing, query_buffer
        if is_processing or not prompt_text.strip():
            return

        valid, err_msg = validate_ai_query(prompt_text)
        if not valid:
            print(f"\n[Validation Notice]: {err_msg}\n")
            display.show_error(err_msg)
            if speech:
                speech.speak(err_msg)
            return

        is_processing = True
        print(f"\n[AI Query] Asking Liquid AI: {prompt_text!r}...")
        
        display.show_ai_processing(prompt_text)
        display.save_screenshot("ai_lcd_thinking.png")
        
        t0 = time.time()
        reply = ai.generate(prompt_text)
        dt = time.time() - t0
        
        if not reply:
            reply = "I apologize, I could not generate a response at this time."
            
        print(f"[AI Reply ({dt:.2f}s)]: {reply}\n")
        display.show_ai_response(reply, query=prompt_text)
        display.save_screenshot("ai_lcd_response.png")
        
        if speech:
            speech.speak(reply)
            
        query_buffer = ""
        is_processing = False

    # Terminal key listener
    if sys.platform != "win32":
        import termios
        import tty
        import select

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            while True:
                r, _, _ = select.select([sys.stdin], [], [], 0.1)
                if r:
                    ch = sys.stdin.read(1)
                    if not ch:
                        continue

                    # ESC or Ctrl+C
                    if ch in ("\x1b", "\x03"):
                        print("\nExiting AI LCD test...")
                        break

                    if is_processing:
                        continue

                    # Hotkey 1
                    if ch == "1" and not query_buffer:
                        threading.Thread(target=ask_ai, args=("What is Braille?",), daemon=True).start()
                        continue
                    # Hotkey 2 (Single-digit math allowed)
                    if ch == "2" and not query_buffer:
                        threading.Thread(target=ask_ai, args=("What is 5 + 3?",), daemon=True).start()
                        continue
                    # Hotkey 3
                    if ch == "3" and not query_buffer:
                        threading.Thread(target=ask_ai, args=("Now let me show you the shape of my heart.",), daemon=True).start()
                        continue
                    # Hotkey 4 (Multi-digit math test -> restricted)
                    if ch == "4" and not query_buffer:
                        threading.Thread(target=ask_ai, args=("What is 15 + 27?",), daemon=True).start()
                        continue

                    # Enter
                    if ch in ("\r", "\n"):
                        if query_buffer.strip():
                            q = query_buffer
                            threading.Thread(target=ask_ai, args=(q,), daemon=True).start()
                        continue

                    # Backspace
                    if ch in ("\x7f", "\b"):
                        if query_buffer:
                            query_buffer = query_buffer[:-1]
                            display.show_ai_query_input(query_buffer)
                            print(f"\rQuery: {query_buffer}  \b", end="", flush=True)
                        continue

                    # Regular printable characters
                    if ch.isprintable():
                        query_buffer += ch
                        display.show_ai_query_input(query_buffer)
                        print(f"\rQuery: {query_buffer}", end="", flush=True)

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    else:
        # Windows simulation
        import msvcrt
        print("Running in Windows interactive simulation mode. Type keys:")
        try:
            while True:
                if msvcrt.kbhit():
                    ch_bytes = msvcrt.getch()
                    if ch_bytes in (b"\x1b", b"\x03"):
                        break
                    try:
                        ch = ch_bytes.decode("utf-8")
                    except Exception:
                        continue

                    if is_processing:
                        continue

                    if ch == "1" and not query_buffer:
                        threading.Thread(target=ask_ai, args=("What is Braille?",), daemon=True).start()
                        continue
                    if ch == "2" and not query_buffer:
                        threading.Thread(target=ask_ai, args=("What is 5 + 3?",), daemon=True).start()
                        continue
                    if ch == "3" and not query_buffer:
                        threading.Thread(target=ask_ai, args=("Now let me show you the shape of my heart.",), daemon=True).start()
                        continue
                    if ch == "4" and not query_buffer:
                        threading.Thread(target=ask_ai, args=("What is 15 + 27?",), daemon=True).start()
                        continue

                    if ch in ("\r", "\n"):
                        if query_buffer.strip():
                            q = query_buffer
                            threading.Thread(target=ask_ai, args=(q,), daemon=True).start()
                        continue

                    if ch == "\x08":  # Backspace
                        if query_buffer:
                            query_buffer = query_buffer[:-1]
                            display.show_ai_query_input(query_buffer)
                            print(f"\rQuery: {query_buffer}  \b", end="", flush=True)
                        continue

                    if ch.isprintable():
                        query_buffer += ch
                        display.show_ai_query_input(query_buffer)
                        print(f"\rQuery: {query_buffer}", end="", flush=True)

                time.sleep(0.02)
        except KeyboardInterrupt:
            pass

    display.clear()
    display.show_status("AI Mode Test Ended.")
    if speech:
        speech.shutdown()
    print("\nAI LCD Test finished.")


if __name__ == "__main__":
    main()
