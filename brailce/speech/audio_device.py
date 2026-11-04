"""
Brailce Audio Device Coordinator
================================

Coordinates exclusive access to the I2S DAC (MAX98357A) and ALSA sound card.
Ensures seamless, clean handoff between speech playback (Piper Neural TTS,
cached keystrokes) and tactile sound effects without ALSA device collisions,
DMA buffer underruns, or loud static noise.

Safe Playback Rules:
1. Always acquire exclusive device lock before opening the audio device.
2. Only one playback process runs at any time.
3. Playback uses the standard mode-introduction pipeline: aplay -q <file.wav>.
   Never stream raw bytes or piped WAV data to aplay via stdin.
4. Allow hardware DMA clock to settle after interrupting any active process.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class AudioDeviceCoordinator:
    """
    Singleton audio coordinator that manages DAC access and active playback
    processes across Piper TTS, cached character WAVs, and sound effects.
    """

    _lock = threading.RLock()
    _active_process: Optional[subprocess.Popen] = None
    _active_owner: Optional[str] = None

    @classmethod
    def get_lock(cls) -> threading.RLock:
        """Get the shared re-entrant audio device lock."""
        return cls._lock

    @classmethod
    def register_process(cls, proc: subprocess.Popen, owner: str) -> None:
        """Register the currently playing audio process."""
        with cls._lock:
            cls._active_process = proc
            cls._active_owner = owner

    @classmethod
    def unregister_process(cls, proc: Optional[subprocess.Popen] = None) -> None:
        """Unregister the active audio process upon completion."""
        with cls._lock:
            if proc is None or cls._active_process is proc:
                cls._active_process = None
                cls._active_owner = None

    @classmethod
    def interrupt_active(cls, target_owner: Optional[str] = None) -> None:
        """
        Immediately terminate the currently playing audio process.
        Gives the hardware a moment to reset the I2S DMA buffer cleanly.
        """
        with cls._lock:
            proc = cls._active_process
            owner = cls._active_owner
            if proc is not None:
                if target_owner is None or owner == target_owner:
                    try:
                        if proc.poll() is None:
                            proc.terminate()
                            try:
                                proc.wait(timeout=0.2)
                            except Exception:
                                proc.kill()
                                try:
                                    proc.wait(timeout=0.1)
                                except Exception:
                                    pass
                    except Exception as exc:
                        logger.debug("Error interrupting active audio process (%s): %s", owner, exc)
                    finally:
                        cls._active_process = None
                        cls._active_owner = None
                        # Allow ALSA I2S DMA clock to settle before the next audio stream opens
                        time.sleep(0.05)

    @classmethod
    def play_wav_file(
        cls,
        wav_path: str,
        owner: str = "audio",
        timeout: float = 15.0,
    ) -> bool:
        """
        Safely play a WAV file using the exact standard mode-introduction pipeline:
            aplay -q <wav_path>
        
        Acquires exclusive device lock, registers the process, waits for completion,
        and unregisters safely. Never streams raw bytes or uses stdin.
        """
        if not wav_path or not os.path.isfile(wav_path):
            logger.debug("Audio file does not exist: %r", wav_path)
            return False

        if sys.platform != "win32":
            with cls._lock:
                proc = None
                try:
                    proc = subprocess.Popen(
                        ["aplay", "-q", wav_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    cls.register_process(proc, owner)
                    proc.wait(timeout=timeout)
                    return proc.returncode == 0
                except subprocess.TimeoutExpired:
                    if proc and proc.poll() is None:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                    logger.debug("Playback timeout for: %s", wav_path)
                    return False
                except Exception as exc:
                    logger.debug("aplay failed for %s: %s", wav_path, exc)
                    return False
                finally:
                    cls.unregister_process(proc)
        else:
            # Windows fallback
            try:
                import winsound
                winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                return True
            except Exception as exc:
                logger.debug("winsound playback failed: %s", exc)
                return False
