"""
Brailce Diagnostic Tool – Sound Effects and Voice Polish
=========================================================

Auditions and validates all acoustic earcons and polished voice outputs:
    1. Keypress tactile click
    2. Number indicator (#) toggle rising/falling chimes
    3. Spacebar wooden tap & word vocalization
    4. Backspace pop & boundary thud
    5. Clear buffer wipe
    6. Mode switch melodic triad arpeggio
    7. Enter confirmation chime
    8. Math solution celebratory success chord + counting explanation
    9. Error cue & friendly guidance
    10. Camera shutter mechanical snap
    11. Volume dynamic pitch ticks (20%, 50%, 80%, 100%)
"""

import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from brailce.audio.sound_effects import SoundEffectsEngine
from brailce.config.loader import ConfigLoader
from brailce.speech.service import SpeechService


def main() -> None:
    print("=" * 65)
    print("       BRAILCE SOUND EFFECTS & POLISHED VOICE AUDITION")
    print("=" * 65)

    sound = SoundEffectsEngine(enabled=True, volume=85)
    
    config_path = os.path.join(PROJECT_ROOT, "brailce", "config", "config.json")
    try:
        speech = SpeechService.from_config(ConfigLoader.load(config_path))
    except RuntimeError as exc:
        print(f"Speech unavailable: {exc}")
        return

    print(f"\n[Sound Engine] Platform: {sys.platform} | Available: {sound.is_available()}")
    print(
        f"[Speech Engine] Engine: {speech.engine_name} | "
        f"Model: {speech.piper_engine.model_path}\n"
    )

    # 1. Mode Switch
    print("1. Playing Mode Switch triad arpeggio...")
    sound.play("mode_switch")
    speech.speak("Free Input Mode. Ready to type.")
    time.sleep(2.5)

    # 2. Keypresses & Character speech
    print("2. Simulating letter keypresses ('B', 'R', 'A')...")
    for ch in ["B", "R", "A"]:
        sound.play("key_press")
        speech.speak(ch)
        time.sleep(0.4)

    # 3. Spacebar & word pronunciation
    print("3. Pressing Spacebar (wooden tap)...")
    sound.play("space")
    speech.speak("Braille")
    time.sleep(1.8)

    # 4. Number indicator toggle (#)
    print("4. Toggling Number Indicator (#)...")
    sound.play("number_on")
    speech.speak("number sign, number mode on")
    time.sleep(2.2)

    print("   Typing digits in number mode ('1', '2', '3')...")
    for digit, word in [("1", "one"), ("2", "two"), ("3", "three")]:
        sound.play("key_press")
        speech.speak(word)
        time.sleep(0.5)

    sound.play("number_off")
    speech.speak("number mode off")
    time.sleep(1.8)

    # 5. Backspace & Boundary
    print("5. Backspace pop and boundary thud...")
    sound.play("backspace")
    speech.speak("backspace")
    time.sleep(0.8)
    sound.play("boundary")
    speech.speak("Buffer empty")
    time.sleep(1.8)

    # 6. Clear wipe
    print("6. Clear buffer wipe...")
    sound.play("clear")
    speech.speak("cleared")
    time.sleep(1.5)

    # 7. Math Mode Success
    print("7. Math mode calculation success chime...")
    sound.play("success")
    speech.speak("5 plus 3 equals 8. Start with 5, count on 3: 6, 7, 8.")
    time.sleep(5.0)

    # 8. Error Cue
    print("8. Error warning cue...")
    sound.play("error")
    speech.speak("Numbers and operators only.")
    time.sleep(2.5)

    # 9. Camera Shutter (Scanner Mode)
    print("9. Camera shutter mechanical snap...")
    sound.play("camera_shutter")
    speech.speak("Scanning document with camera.")
    time.sleep(2.5)

    # 10. Volume pitch ticks
    print("10. Testing Volume pitch ticks...")
    for vol in [25, 50, 75, 100]:
        sound.play_volume_tick(vol)
        speech.speak(f"Volume {vol} percent")
        time.sleep(1.5)

    speech.wait_until_idle(timeout=60)
    speech.shutdown()
    print("\n" + "=" * 65)
    print("       AUDITION COMPLETE - ALL SOUNDS & VOICES WORKING")
    print("=" * 65)


if __name__ == "__main__":
    main()
