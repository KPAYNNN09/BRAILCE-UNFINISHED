"""
Brailce eSpeak NG Engine – Offline Speech
============================================

Uses eSpeak NG for lightweight, zero-latency offline text-to-speech.
Implements a speech queue to handle rapid key presses
without overlapping audio.
"""

from __future__ import annotations

import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from typing import Optional

from brailce.speech.audio_device import AudioDeviceCoordinator
from brailce.speech.base import SpeechEngine
from brailce.speech.normalizer import normalize_for_espeak_character, is_keystroke_feedback

logger = logging.getLogger(__name__)


def _find_espeak_binary() -> Optional[str]:
    """Locate the espeak-ng or espeak executable on the system."""
    # 1. System PATH
    found = shutil.which("espeak-ng") or shutil.which("espeak")
    if found:
        return found

    # 2. Windows standard installation locations
    if sys.platform == "win32":
        for cand in [
            r"C:\Program Files\eSpeak NG\espeak-ng.exe",
            r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe",
            r"C:\Program Files\eSpeak\command_line\espeak.exe",
        ]:
            if os.path.isfile(cand):
                return cand

    # 3. Linux / Raspberry Pi standard locations
    for cand in [
        "/usr/bin/espeak-ng",
        "/usr/local/bin/espeak-ng",
        "/usr/bin/espeak",
        "/usr/local/bin/espeak",
    ]:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand

    return None


def clean_speech_text(text: str) -> str:
    """
    Polish raw input, markdown, and symbols into natural, cadence-friendly speech.
    Removes markdown tokens, converts ellipsis to natural pauses, and normalizes spacing.
    """
    if not text:
        return ""

    trimmed = text.strip()
    if not trimmed:
        return ""

    # If single character or short single letter, format for terminal pitch
    if len(trimmed) == 1:
        if trimmed.isalpha():
            return trimmed.upper() + "."
        elif trimmed.isdigit():
            return trimmed + "."
        return trimmed

    s = text
    # 1. Strip markdown bold/italics
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    s = re.sub(r"__([^_]+)__", r"\1", s)
    s = re.sub(r"_([^_]+)_", r"\1", s)

    # 2. Strip code blocks and backticks
    s = re.sub(r"```[a-zA-Z]*\n?([\s\S]*?)```", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)

    # 3. Strip headers like '### Heading'
    s = re.sub(r"^#{1,6}\s*", "", s, flags=re.MULTILINE)

    # 4. Strip bullets and markdown dashes
    s = re.sub(r"^[•\*\-\+]\s+", "", s, flags=re.MULTILINE)
    s = s.replace("•", "").replace("–", "-").replace("—", ", ")

    # 5. Natural pause normalization for counting numbers (e.g. "6, 7, 8" -> "6. 7. 8.")
    # Prevents eSpeak from rushing through counting sequences like an auctioneer
    s = re.sub(r"(\b\d+)\s*,\s*(?=\d+\b)", r"\1. ", s)
    s = s.replace("...", ". ")

    # 6. Normalize multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


class EspeakEngine(SpeechEngine):
    """
    eSpeak NG text-to-speech engine.

    Speech requests are queued and processed sequentially in a
    background thread so rapid key presses produce ordered,
    non-overlapping audio.

    On Raspberry Pi with I2S DAC (MAX98357A), a short silence preamble
    is prepended to each utterance to compensate for ALSA cold-start
    latency that would otherwise clip the first ~300ms of audio.
    """

    def __init__(
        self,
        voice: str = "en-us+m3",
        rate: int = 165,
        volume: int = 100,
        pitch: int = 52,
        word_gap: int = 5,
        max_queue_size: int = 50,
    ) -> None:
        self._voice = voice
        self._rate = rate
        self._volume = volume
        self._pitch = pitch
        self._word_gap = word_gap
        self._queue: queue.Queue[Optional[str]] = queue.Queue(maxsize=max_queue_size)
        self._worker: Optional[threading.Thread] = None
        self._running = False
        self._binary = _find_espeak_binary()
        self._current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    @property
    def engine_name(self) -> str:
        return "eSpeak NG"

    def speak(self, text: str, interrupt: Optional[bool] = None) -> None:
        """
        Enqueue text for sequential, non-overlapping speech output.

        If interrupt is explicitly True, existing pending queue items are cleared
        and the active utterance is cut off immediately.
        Otherwise (default), text is placed in the FIFO queue and plays in order.
        """
        if not text:
            return

        should_interrupt = bool(interrupt)

        if should_interrupt:
            self.stop_current()

        if not self._running:
            self._start_worker()

        try:
            self._queue.put_nowait(text)
        except queue.Full:
            logger.warning("Speech queue full — dropping: %r", text)

    def stop_current(self) -> None:
        """Clear the queue and terminate the active speaking process (espeak or aplay)."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        AudioDeviceCoordinator.interrupt_active("espeak")
        with self._lock:
            if self._current_process and self._current_process.poll() is None:
                try:
                    self._current_process.terminate()
                    self._current_process.wait(timeout=0.5)
                except Exception:
                    try:
                        self._current_process.kill()
                    except Exception:
                        pass
                self._current_process = None

    def stop(self) -> None:
        """Stop speech and shutdown worker thread. Worker is restarted on next speak()."""
        self.stop_current()
        self._running = False
        if self._worker and self._worker.is_alive():
            try:
                self._queue.put_nowait(None)  # Sentinel to unblock worker
            except queue.Full:
                pass
            self._worker.join(timeout=2.0)
        self._worker = None

    def is_available(self) -> bool:
        """Check if eSpeak NG is installed."""
        bin_path = self._binary or _find_espeak_binary()
        if bin_path:
            try:
                result = subprocess.run(
                    [bin_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return True
            except Exception:
                pass

        try:
            result = subprocess.run(
                ["espeak-ng", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except FileNotFoundError:
            try:
                result = subprocess.run(
                    ["espeak", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0
            except FileNotFoundError:
                if sys.platform == "win32":
                    try:
                        import comtypes.client
                        return True
                    except ImportError:
                        return False
                return False
        except Exception:
            return False

    def set_voice(self, voice: str) -> None:
        self._voice = voice

    def set_rate(self, rate: int) -> None:
        self._rate = max(80, min(500, rate))

    def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(200, volume))

    def set_pitch(self, pitch: int) -> None:
        self._pitch = max(0, min(99, pitch))

    def set_word_gap(self, word_gap: int) -> None:
        self._word_gap = max(0, min(100, word_gap))

    # ---- Worker Thread ----

    def _start_worker(self) -> None:
        """Start the background speech worker thread."""
        self._running = True
        self._worker = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="espeak-worker",
        )
        self._worker.start()

    def _worker_loop(self) -> None:
        """Process speech queue items sequentially."""
        if sys.platform == "win32":
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except ImportError:
                pass

        while self._running:
            try:
                text = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if text is None:
                break

            self._speak_sync(text)

        if sys.platform == "win32":
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except ImportError:
                pass

    def _speak_sync(self, text: str) -> None:
        """Execute a single speech request synchronously using eSpeak NG.

        On Linux (Raspberry Pi), uses --stdout piped to aplay with a silence
        preamble to prevent ALSA I2S DAC cold-start from clipping the beginning
        of the utterance.
        """
        speech_text = clean_speech_text(text)
        if not speech_text:
            return

        bin_path = self._binary or _find_espeak_binary()

        # On Linux/Pi: use --stdout → prepend silence → pipe to aplay
        # This prevents the MAX98357A I2S DAC from clipping the first ~300ms
        if sys.platform != "win32" and bin_path:
            try:
                cmd = [
                    bin_path,
                    "-v", self._voice,
                    "-s", str(self._rate),
                    "-a", str(self._volume),
                    "-g", str(self._word_gap),
                    "-p", str(self._pitch),
                    "--stdout",
                    speech_text,
                ]
                espeak_proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=25,
                )
                if espeak_proc.returncode == 0:
                    wav_data = getattr(espeak_proc, "stdout", None)
                    if isinstance(wav_data, (bytes, bytearray)) and len(wav_data) > 0:
                        # Prepend ~350ms of silence (22050 Hz * 16-bit mono = 15434 bytes)
                        # to give MAX98357A I2S DAC sufficient time to power on and lock its clock
                        silence_samples = 7717  # ~350ms at 22050 Hz
                        silence_bytes = b'\x00\x00' * silence_samples  # 16-bit silence
                        data_pos = wav_data.find(b'data')
                        if data_pos != -1 and len(wav_data) >= data_pos + 8:
                            # Rebuild WAV: header + silence + original audio data
                            import struct as _struct
                            header = bytearray(wav_data[:data_pos + 8])
                            audio_data = wav_data[data_pos + 8:]
                            new_audio = silence_bytes + audio_data
                            # Update data chunk size (bytes at data_pos+4 to data_pos+8)
                            new_data_size = len(new_audio)
                            header[data_pos + 4 : data_pos + 8] = _struct.pack('<I', new_data_size)
                            # Update RIFF chunk size (bytes 4-7)
                            header[4:8] = _struct.pack('<I', len(header) - 8 + new_data_size)
                            full_wav = bytes(header) + new_audio
                        else:
                            full_wav = wav_data

                        # Pipe to aplay for playback
                        with self._lock:
                            aplay_proc = subprocess.Popen(
                                ["aplay", "-q"],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            self._current_process = aplay_proc
                        AudioDeviceCoordinator.register_process(aplay_proc, "espeak")
                        try:
                            aplay_proc.communicate(input=full_wav, timeout=30)
                        except subprocess.TimeoutExpired:
                            aplay_proc.kill()
                        finally:
                            with self._lock:
                                self._current_process = None
                            AudioDeviceCoordinator.unregister_process(aplay_proc)
                return
            except subprocess.TimeoutExpired:
                return
            except FileNotFoundError:
                pass
            except Exception as exc:
                logger.debug("eSpeak --stdout pipeline failed: %s", exc)
                # Fall through to direct execution

        # Direct execution (Windows or fallback)
        if bin_path or sys.platform != "win32":
            cmd = bin_path or "espeak-ng"
            try:
                res = subprocess.run(
                    [
                        cmd,
                        "-v", self._voice,
                        "-s", str(self._rate),
                        "-a", str(self._volume),
                        "-g", str(self._word_gap),
                        "-p", str(self._pitch),
                        speech_text,
                    ],
                    capture_output=True,
                    timeout=25,
                )
                if res.returncode == 0 or not isinstance(res.returncode, int):
                    return
            except subprocess.TimeoutExpired:
                return
            except FileNotFoundError:
                pass
            except Exception as exc:
                logger.debug("eSpeak execution failed: %s", exc)

        # Fallback: Windows SAPI5 via comtypes (prevents pyttsx3 runAndWait thread deadlocks)
        if sys.platform == "win32":
            try:
                if getattr(self, "_sapi_engine", None) is None:
                    import comtypes.client
                    self._sapi_engine = comtypes.client.CreateObject("SAPI.SpVoice")

                    # Try to select the clearest American voice (Zira)
                    voices = self._sapi_engine.GetVoices()
                    for i in range(voices.Count):
                        desc = voices.Item(i).GetDescription()
                        if "Zira" in desc:
                            self._sapi_engine.Voice = voices.Item(i)
                            break

                # SAPI expects volume 0-100
                self._sapi_engine.Volume = min(100, max(0, self._volume))
                sapi_rate = max(-10, min(10, (self._rate - 160) // 15))
                self._sapi_engine.Rate = sapi_rate

                # Speak flag 0 = synchronous
                self._sapi_engine.Speak(speech_text, 0)
                return
            except Exception as e:
                logger.debug("SAPI fallback failed: %s", e)

        logger.error(
            "Neither espeak-ng nor espeak found. "
            "Install eSpeak NG: https://github.com/espeak-ng/espeak-ng"
        )
