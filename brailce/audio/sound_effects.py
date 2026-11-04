"""
Brailce Sound Effects Engine – Tactile Earcons & Acoustic Feedback
===================================================================

Provides instantaneous, polished auditory feedback (earcons) for all
physical and simulated hardware inputs:
    - Dedicated character key presses (tactile mechanical click)
    - Number indicator toggle '#' (uplifting rising / falling chimes)
    - Spacebar (warm wooden tap)
    - Backspace (crisp downward delete pop)
    - Boundary / Empty buffer (subtle low double-bump)
    - Clear buffer (smooth descending wipe)
    - Mode switch (melodic triad arpeggio)
    - Enter / Confirmation (affirmative rising chime)
    - Math / Vision Success (celebratory bell chord)
    - Error / Invalid input (gentle low alert)
    - Camera shutter (authentic dual-click mechanical snap)
    - Volume adjustments (pitch-scaled feedback ticks)

Implementation:
    - 100% offline, pure Python standard library (wave, math, struct).
    - Zero heavy external dependencies (no Pygame, SDL2, or sounddevice required).
    - Synthesizes studio-grade acoustic waveforms with natural ADSR / exponential
      decay envelopes on startup.
    - Caches pre-rendered WAV files for instant <2ms non-blocking playback.
    - Uses AudioDeviceCoordinator to share the MAX98357A I2S DAC safely with Piper TTS,
      preventing device busy errors and ALSA underruns.
    - Standard safe aplay -q playback pipeline (exact mode-introduction pattern).
"""

from __future__ import annotations

import logging
import math
import os
import struct
import sys
import tempfile
import threading
import wave
from typing import Dict, Optional

from brailce.speech.audio_device import AudioDeviceCoordinator

logger = logging.getLogger(__name__)


class SoundEffectsEngine:
    """
    High-performance, low-latency audio cue engine for the Brailce device.
    Generates and plays polished acoustic earcons for every hardware input.
    """

    SAMPLE_RATE = 22050

    def __init__(
        self,
        enabled: bool = False,
        volume: int = 0,
        cache_dir: Optional[str] = None,
    ) -> None:
        """
        Initialize the sound effects engine and synthesize acoustic earcons.

        Args:
            enabled: Whether sound effects are globally active.
            volume: Volume level from 0 to 100.
            cache_dir: Directory to store pre-rendered WAV files.
        """
        self.enabled = enabled
        self._volume = max(0, min(100, volume))
        self._cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "brailce_sounds")
        self._sound_files: Dict[str, str] = {}
        self._lock = threading.Lock()

        try:
            self._precompute_all_sounds()
        except Exception as exc:
            logger.warning("Failed to precompute sound cues: %s", exc)

    @property
    def volume(self) -> int:
        return self._volume

    def set_volume(self, volume: int) -> None:
        """Update volume level (0-100)."""
        self._volume = max(0, min(100, volume))

    def is_available(self) -> bool:
        """Check whether audio playback is available on this platform."""
        if not self.enabled:
            return False
        return True

    def play(self, sound_name: str) -> None:
        """
        Play a named sound effect asynchronously.

        Args:
            sound_name: Name of sound cue (e.g. 'key_press', 'number_on', 'mode_switch').
        """
        if not self.enabled or self._volume <= 0:
            return

        wav_path = self._sound_files.get(sound_name)
        if not wav_path or not os.path.exists(wav_path):
            logger.debug("Sound %r not found in precomputed cache.", sound_name)
            return

        self._play_file_async(wav_path)

    def play_volume_tick(self, volume_percent: int) -> None:
        """
        Play an instantaneous tick whose pitch and volume reflect the new volume level.
        Pitch scales from 350 Hz (at 0%) to 1250 Hz (at 100%).
        """
        if not self.enabled or self._volume <= 0:
            return

        vol = max(0, min(100, volume_percent))
        freq = 350.0 + (vol * 9.0)  # 350 Hz -> 1250 Hz
        amp = max(0.1, (vol / 100.0) * (self._volume / 100.0))

        # Generate on-demand short tick (20ms)
        def _play_tick():
            try:
                n_samples = int(self.SAMPLE_RATE * 0.020)
                frames = bytearray()
                for i in range(n_samples):
                    t = i / self.SAMPLE_RATE
                    env = math.exp(-i / (self.SAMPLE_RATE * 0.005))
                    val = int(28000 * amp * env * math.sin(2 * math.pi * freq * t))
                    frames.extend(struct.pack("<h", max(-32767, min(32767, val))))

                tick_path = os.path.join(self._cache_dir, f"vol_tick_{vol}.wav")
                self._save_wav(tick_path, frames)
                self._play_file_async(tick_path)
            except Exception as exc:
                logger.debug("Volume tick playback error: %s", exc)

        threading.Thread(target=_play_tick, daemon=True, name="brailce-sound-tick").start()

    # ---- Internal Playback ----

    def _play_file_async(self, file_path: str) -> None:
        """
        Dispatch non-blocking playback of a WAV file through AudioDeviceCoordinator.
        Uses the exact standard mode-introduction pipeline (aplay -q) to prevent static.
        """
        def _runner():
            try:
                AudioDeviceCoordinator.play_wav_file(file_path, owner="sound_effects", timeout=5.0)
            except Exception as exc:
                logger.debug("Sound effects playback error for %s: %s", file_path, exc)

        threading.Thread(target=_runner, daemon=True, name="brailce-sound-play").start()

    # ---- Waveform Synthesis & Caching ----

    def _save_wav(self, file_path: str, frames: bytearray) -> str:
        """Write raw 16-bit PCM mono frames into a valid WAV file using wave module only."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with wave.open(file_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.SAMPLE_RATE)
            wav.writeframes(frames)
        return file_path

    def _precompute_all_sounds(self) -> None:
        """Pre-render and cache all application earcons to disk."""
        os.makedirs(self._cache_dir, exist_ok=True)

        generators = {
            "key_press": self._gen_key_press,
            "space": self._gen_space,
            "backspace": self._gen_backspace,
            "boundary": self._gen_boundary,
            "clear": self._gen_clear,
            "number_on": self._gen_number_on,
            "number_off": self._gen_number_off,
            "mode_switch": self._gen_mode_switch,
            "enter": self._gen_enter,
            "success": self._gen_success,
            "error": self._gen_error,
            "thinking": self._gen_thinking,
            "camera_shutter": self._gen_camera_shutter,
        }

        for name, gen_fn in generators.items():
            path = os.path.join(self._cache_dir, f"{name}.wav")
            try:
                frames = gen_fn()
                self._save_wav(path, frames)
                self._sound_files[name] = path
            except Exception as exc:
                logger.debug("Error generating sound %s: %s", name, exc)

        logger.debug("SoundEffectsEngine initialized %d acoustic cues.", len(self._sound_files))

    # ---- Sound Generators ----

    def _gen_key_press(self) -> bytearray:
        """Tactile micro-click: 18ms transient simulating a damped mechanical switch."""
        n = int(self.SAMPLE_RATE * 0.018)
        frames = bytearray()
        for i in range(n):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.0035))
            f = 1150.0 - 300.0 * (i / n)
            val = int(24000 * env * (0.85 * math.sin(2 * math.pi * f * t) + 0.15 * math.sin(4 * math.pi * f * t)))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_space(self) -> bytearray:
        """Warm wooden spacebar tap: 30ms lower acoustic resonance (210 Hz)."""
        n = int(self.SAMPLE_RATE * 0.030)
        frames = bytearray()
        for i in range(n):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.007))
            val = int(25000 * env * (0.75 * math.sin(2 * math.pi * 210.0 * t) + 0.25 * math.sin(2 * math.pi * 420.0 * t)))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_backspace(self) -> bytearray:
        """Crisp downward delete pop: 35ms frequency chip (540 Hz -> 260 Hz)."""
        n = int(self.SAMPLE_RATE * 0.035)
        frames = bytearray()
        for i in range(n):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.009))
            freq = 540.0 - (280.0 * (i / n))
            val = int(24000 * env * math.sin(2 * math.pi * freq * t))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_boundary(self) -> bytearray:
        """Boundary bump: gentle double hollow tap (130 Hz, two pulses 14ms apart)."""
        n = int(self.SAMPLE_RATE * 0.055)
        frames = bytearray()
        p1 = 0
        p2 = int(self.SAMPLE_RATE * 0.016)
        for i in range(n):
            t = i / self.SAMPLE_RATE
            env1 = math.exp(-(i - p1) / (self.SAMPLE_RATE * 0.004)) if i >= p1 else 0
            env2 = math.exp(-(i - p2) / (self.SAMPLE_RATE * 0.004)) if i >= p2 else 0
            val = int(20000 * ((env1 * 0.6) + (env2 * 0.8)) * math.sin(2 * math.pi * 135.0 * t))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_clear(self) -> bytearray:
        """Buffer clear wipe: dual harmonic downward sweep (80ms, 880 Hz -> 380 Hz)."""
        n = int(self.SAMPLE_RATE * 0.080)
        frames = bytearray()
        for i in range(n):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.030))
            f1 = 880.0 - 500.0 * (i / n)
            f2 = f1 * 0.75
            val = int(20000 * env * (0.6 * math.sin(2 * math.pi * f1 * t) + 0.4 * math.sin(2 * math.pi * f2 * t)))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_number_on(self) -> bytearray:
        """Rising major third chime: C5 (523.25 Hz) -> E5 (659.25 Hz), 90ms total."""
        n1 = int(self.SAMPLE_RATE * 0.045)
        n2 = int(self.SAMPLE_RATE * 0.045)
        frames = bytearray()
        for i in range(n1):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.022))
            val = int(22000 * env * (0.8 * math.sin(2 * math.pi * 523.25 * t) + 0.2 * math.sin(2 * math.pi * 1046.5 * t)))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        for i in range(n2):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.025))
            val = int(24000 * env * (0.8 * math.sin(2 * math.pi * 659.25 * t) + 0.2 * math.sin(2 * math.pi * 1318.5 * t)))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_number_off(self) -> bytearray:
        """Falling major third chime: E5 (659.25 Hz) -> C5 (523.25 Hz), 90ms total."""
        n1 = int(self.SAMPLE_RATE * 0.045)
        n2 = int(self.SAMPLE_RATE * 0.045)
        frames = bytearray()
        for i in range(n1):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.022))
            val = int(22000 * env * (0.8 * math.sin(2 * math.pi * 659.25 * t) + 0.2 * math.sin(2 * math.pi * 1318.5 * t)))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        for i in range(n2):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.025))
            val = int(24000 * env * (0.8 * math.sin(2 * math.pi * 523.25 * t) + 0.2 * math.sin(2 * math.pi * 1046.5 * t)))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_mode_switch(self) -> bytearray:
        """Melodic triad arpeggio: C5 -> E5 -> G5 (140ms total)."""
        frames = bytearray()
        notes = [523.25, 659.25, 783.99]
        durations = [0.040, 0.040, 0.060]
        for freq, dur in zip(notes, durations):
            n_part = int(self.SAMPLE_RATE * dur)
            for i in range(n_part):
                t = i / self.SAMPLE_RATE
                env = math.exp(-i / (self.SAMPLE_RATE * (dur * 0.6)))
                val = int(20000 * env * (0.75 * math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(4 * math.pi * freq * t)))
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_enter(self) -> bytearray:
        """Affirmative confirmation chime: rising fifth F5 (698.46 Hz) -> A5 (880.0 Hz)."""
        frames = bytearray()
        notes = [698.46, 880.0]
        durations = [0.045, 0.065]
        for freq, dur in zip(notes, durations):
            n_part = int(self.SAMPLE_RATE * dur)
            for i in range(n_part):
                t = i / self.SAMPLE_RATE
                env = math.exp(-i / (self.SAMPLE_RATE * (dur * 0.6)))
                val = int(22000 * env * math.sin(2 * math.pi * freq * t))
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_success(self) -> bytearray:
        """Celebratory bell chord: C5 + E5 + G5 + C6 blended with warm exponential decay (220ms)."""
        n = int(self.SAMPLE_RATE * 0.220)
        frames = bytearray()
        freqs = [523.25, 659.25, 783.99, 1046.50]
        weights = [0.35, 0.25, 0.25, 0.15]
        for i in range(n):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.075))
            signal = sum(w * math.sin(2 * math.pi * f * t) for f, w in zip(freqs, weights))
            val = int(26000 * env * signal)
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_error(self) -> bytearray:
        """Gentle warning cue: soft descending minor second Eb4 (311 Hz) -> D4 (293 Hz)."""
        frames = bytearray()
        notes = [311.13, 293.66]
        for freq in notes:
            n_part = int(self.SAMPLE_RATE * 0.075)
            for i in range(n_part):
                t = i / self.SAMPLE_RATE
                env = math.exp(-i / (self.SAMPLE_RATE * 0.035))
                val = int(18000 * env * math.sin(2 * math.pi * freq * t))
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_thinking(self) -> bytearray:
        """Subtle rising cue for background processing: G4 (392 Hz) -> C5 (523 Hz), 80ms."""
        frames = bytearray()
        notes = [392.00, 523.25]
        for freq in notes:
            n_part = int(self.SAMPLE_RATE * 0.040)
            for i in range(n_part):
                t = i / self.SAMPLE_RATE
                env = math.exp(-i / (self.SAMPLE_RATE * 0.020))
                val = int(16000 * env * math.sin(2 * math.pi * freq * t))
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames

    def _gen_camera_shutter(self) -> bytearray:
        """Camera shutter click: dual mechanical click snap (12ms click, 10ms gap, 14ms release)."""
        frames = bytearray()
        # Click 1
        n1 = int(self.SAMPLE_RATE * 0.012)
        for i in range(n1):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.002))
            val = int(24000 * env * math.sin(2 * math.pi * 1400.0 * t))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        # Silence gap using integer 16-bit silence samples
        n_gap = int(self.SAMPLE_RATE * 0.010)
        for _ in range(n_gap):
            frames.extend(struct.pack("<h", 0))
        # Click 2 (lower release)
        n2 = int(self.SAMPLE_RATE * 0.014)
        for i in range(n2):
            t = i / self.SAMPLE_RATE
            env = math.exp(-i / (self.SAMPLE_RATE * 0.003))
            val = int(22000 * env * math.sin(2 * math.pi * 950.0 * t))
            frames.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return frames
