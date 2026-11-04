"""Single Piper TTS and playback pipeline for all Brailce speech."""

from __future__ import annotations

import hashlib
import inspect
import itertools
import json
import logging
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import wave
from array import array
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from brailce.speech.audio_device import AudioDeviceCoordinator
from brailce.speech.base import SpeechEngine
from brailce.config.defaults import DEFAULT_CONFIG
from brailce.speech.normalizer import normalize_for_piper
from brailce.speech.pronunciation import CHARACTER_PRONUNCIATIONS

logger = logging.getLogger(__name__)

_DEFAULT_SPEECH_SETTINGS = DEFAULT_CONFIG["speech"]
_SUPPORTED_SETTINGS = (
    "length_scale",
    "noise_scale",
    "noise_w",
    "sentence_silence",
    "leading_silence_ms",
    "trailing_silence_ms",
    "volume",
)


def _find_piper_binary() -> Optional[str]:
    found = shutil.which("piper")
    if found:
        return found
    home = Path.home()
    candidates = (
        home / "piper" / "piper" / "piper",
        home / "piper" / "piper" / "piper.exe",
        Path("/usr/local/bin/piper"),
        Path("/usr/bin/piper"),
    )
    return next((str(path) for path in candidates if path.is_file()), None)


def _cache_fingerprint(
    model_path: str,
    model_config_path: str,
    settings: Dict[str, Any],
    speaker_id: Optional[int],
) -> str:
    """Hash model identity and all synthesis settings that affect cached audio."""
    model_stat = Path(model_path).stat()
    config_stat = Path(model_config_path).stat()
    identity = {
        "model": str(Path(model_path).resolve()),
        "model_size": model_stat.st_size,
        "model_mtime_ns": model_stat.st_mtime_ns,
        "config_size": config_stat.st_size,
        "config_mtime_ns": config_stat.st_mtime_ns,
        "settings": {key: settings[key] for key in _SUPPORTED_SETTINGS},
        "speaker_id": speaker_id,
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode("utf-8")
    ).hexdigest()[:20]


class PiperEngine(SpeechEngine):
    """Queued Piper speech with a persistent Python voice when available."""

    def __init__(
        self,
        binary_path: Optional[str] = None,
        model_path: Optional[str] = None,
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w: Optional[float] = None,
        sentence_silence: Optional[float] = None,
        leading_silence_ms: Optional[int] = None,
        trailing_silence_ms: Optional[int] = None,
        volume: Optional[int] = None,
        speaker_id: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        cache_root: Optional[str] = None,
    ) -> None:
        self._binary = binary_path or _find_piper_binary()
        configured_model = model_path or str(_DEFAULT_SPEECH_SETTINGS["model_path"])
        self._model = str(Path(configured_model).expanduser()) if configured_model else None
        self._model_config = f"{self._model}.json" if self._model else None
        self._settings: Dict[str, Any] = {
            "length_scale": float(
                _DEFAULT_SPEECH_SETTINGS["length_scale"]
                if length_scale is None else length_scale
            ),
            "noise_scale": float(
                _DEFAULT_SPEECH_SETTINGS["noise_scale"]
                if noise_scale is None else noise_scale
            ),
            "noise_w": float(
                _DEFAULT_SPEECH_SETTINGS["noise_w"] if noise_w is None else noise_w
            ),
            "sentence_silence": float(
                _DEFAULT_SPEECH_SETTINGS["sentence_silence"]
                if sentence_silence is None else sentence_silence
            ),
            "leading_silence_ms": max(
                0,
                int(
                    _DEFAULT_SPEECH_SETTINGS["leading_silence_ms"]
                    if leading_silence_ms is None else leading_silence_ms
                ),
            ),
            "trailing_silence_ms": max(
                0,
                int(
                    _DEFAULT_SPEECH_SETTINGS["trailing_silence_ms"]
                    if trailing_silence_ms is None else trailing_silence_ms
                ),
            ),
            "volume": max(
                0,
                min(
                    100,
                    int(
                        _DEFAULT_SPEECH_SETTINGS["volume"]
                        if volume is None else volume
                    ),
                ),
            ),
        }
        self._speaker_id = speaker_id
        self._cache_root = Path(cache_root) if cache_root else self._default_cache_root()
        self._cache_dir: Optional[Path] = None
        self._queue: queue.Queue[Optional[Tuple[str, Optional[str]]]] = queue.Queue(
            maxsize=max_queue_size or int(_DEFAULT_SPEECH_SETTINGS["max_queue_size"])
        )
        self._worker: Optional[threading.Thread] = None
        self._cache_worker: Optional[threading.Thread] = None
        self._running = False
        self._current_process: Optional[subprocess.Popen[bytes]] = None
        self._process_lock = threading.Lock()
        self._synthesis_lock = threading.Lock()
        self._voice: Any = None
        self._python_api_checked = False
        self._python_api_failed = False

        if self.is_available():
            self._refresh_cache_dir()
            self._start_cache_generation()

    @staticmethod
    def _default_cache_root() -> Path:
        cache_home = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
        return Path(cache_home) / "brailce" / "speech" if cache_home else (
            Path.home() / ".cache" / "brailce" / "speech"
        )

    @property
    def engine_name(self) -> str:
        return "Piper Neural TTS"

    @property
    def model_path(self) -> Optional[str]:
        return self._model

    @property
    def model_config_path(self) -> Optional[str]:
        return self._model_config

    @property
    def settings(self) -> Dict[str, Any]:
        return dict(self._settings)

    @property
    def speaker_id(self) -> Optional[int]:
        return self._speaker_id

    @property
    def sample_rate(self) -> Optional[int]:
        if not self._model_config:
            return None
        try:
            with open(self._model_config, "r", encoding="utf-8") as config_file:
                model_config = json.load(config_file)
            return int(model_config["audio"]["sample_rate"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def is_available(self) -> bool:
        if not self._binary:
            self._binary = _find_piper_binary()
        if not self._model or not Path(self._model).is_file():
            return False
        if not self._model_config or not Path(self._model_config).is_file():
            return False
        return bool(
            (self._binary and Path(self._binary).is_file())
            or self._python_api_available()
        )

    def _python_api_available(self) -> bool:
        try:
            from piper import PiperVoice  # noqa: F401
            return True
        except ImportError:
            return False

    def set_voice(self, voice: str) -> None:
        model_path = str(Path(voice).expanduser())
        self._model = model_path
        self._model_config = f"{model_path}.json"
        self._voice = None
        self._python_api_checked = False
        self._refresh_cache_dir()
        self._start_cache_generation()

    def set_rate(self, rate: int) -> None:
        logger.warning("Piper rate is configured through speech.length_scale, not WPM.")

    def set_volume(self, volume: int) -> None:
        self._settings["volume"] = max(0, min(100, int(volume)))
        self._refresh_cache_dir()
        self._start_cache_generation()

    def stop(self) -> None:
        self._running = False
        self._clear_queue()
        AudioDeviceCoordinator.interrupt_active("piper")
        with self._process_lock:
            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
        if self._worker and self._worker.is_alive():
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                pass
            if threading.current_thread() is not self._worker:
                self._worker.join(timeout=2.0)
        self._worker = None

    def stop_current(self) -> None:
        self.stop()

    def speak_character(self, character: str, spoken_text: str) -> None:
        """Queue one canonical character pronunciation and use its cached WAV."""
        key = character.upper()
        self._enqueue(spoken_text, key if key in CHARACTER_PRONUNCIATIONS else None)

    def speak(self, text: str, interrupt: Optional[bool] = None) -> None:
        if not text:
            return
        normalized = normalize_for_piper(text)
        if normalized:
            self._enqueue(normalized, None, interrupt=bool(interrupt))

    def _enqueue(
        self,
        text: str,
        cache_key: Optional[str],
        interrupt: bool = False,
    ) -> None:
        if not text:
            return
        if interrupt:
            self._clear_queue()
            AudioDeviceCoordinator.interrupt_active("piper")
        if self._worker is None or not self._worker.is_alive():
            self._running = True
            self._worker = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="piper-worker",
            )
            self._worker.start()
        try:
            self._queue.put_nowait((text, cache_key))
        except queue.Full:
            logger.warning("Piper speech queue full; dropping utterance %r", text)

    def _clear_queue(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                return

    def _worker_loop(self) -> None:
        while self._running:
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if item is None:
                    return
                text, cache_key = item
                self._speak_sync(text, cache_key)
            finally:
                self._queue.task_done()

    def wait_until_idle(self, timeout: Optional[float] = None) -> bool:
        """Wait for queued playback; intended for diagnostics and tests."""
        deadline = time.monotonic() + timeout if timeout is not None else None
        while self._queue.unfinished_tasks:
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(0.05)
        return True

    def _speak_sync(self, text: str, cache_key: Optional[str]) -> None:
        cached_path = self._cache_path(cache_key) if cache_key else None
        if cached_path and cached_path.is_file():
            played = AudioDeviceCoordinator.play_wav_file(
                str(cached_path), owner="piper", timeout=30.0
            )
            if not played:
                logger.error("Piper audio playback failed for character %r", cache_key)
            return

        self._synthesize_and_play(text, cache_key)

    def _synthesize_and_play(self, text: str, cache_key: Optional[str]) -> None:
        if not self.is_available():
            logger.error(self.availability_error())
            return
        fd, temp_name = tempfile.mkstemp(prefix="brailce_piper_", suffix=".wav")
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            with self._synthesis_lock:
                if not self._synthesize(text, temp_path):
                    logger.error("Piper failed to synthesize speech: %r", text)
                    return
                self._prepare_wav(temp_path)
                if cache_key:
                    target = self._cache_path(cache_key)
                    if target:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        temp_cache = target.with_suffix(".tmp.wav")
                        shutil.copyfile(temp_path, temp_cache)
                        os.replace(temp_cache, target)
            playback_path = self._cache_path(cache_key) if cache_key else temp_path
            if playback_path and playback_path.is_file():
                played = AudioDeviceCoordinator.play_wav_file(
                    str(playback_path), owner="piper", timeout=30.0
                )
                if not played:
                    logger.error("Piper audio playback failed for %r", text)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove temporary speech file %s", temp_path)

    def _synthesize(self, text: str, output_path: Path) -> bool:
        if self._synthesize_with_python(text, output_path):
            return True
        return self._synthesize_with_cli(text, output_path)

    def _load_python_voice(self) -> Any:
        if self._python_api_checked:
            return self._voice
        self._python_api_checked = True
        try:
            from piper import PiperVoice
            parameters = inspect.signature(PiperVoice.load).parameters
            load_args: Dict[str, Any] = {}
            if "config_path" in parameters and self._model_config:
                load_args["config_path"] = self._model_config
            self._voice = PiperVoice.load(self._model, **load_args)
        except ImportError:
            self._python_api_failed = True
        except Exception as exc:
            self._python_api_failed = True
            logger.warning("Could not load the Piper Python API; using Piper CLI: %s", exc)
        return self._voice

    def _synthesize_with_python(self, text: str, output_path: Path) -> bool:
        if self._python_api_failed:
            return False
        voice = self._load_python_voice()
        if voice is None:
            return False
        try:
            synthesize = voice.synthesize
            parameters = inspect.signature(synthesize).parameters
            kwargs: Dict[str, Any] = {}
            synthesis_config = self._make_synthesis_config()
            if synthesis_config is not None and "syn_config" in parameters:
                kwargs["syn_config"] = synthesis_config
            else:
                for key in ("length_scale", "noise_scale", "noise_w"):
                    if key in parameters:
                        kwargs[key] = self._settings[key]
            if self._speaker_id is not None and "speaker_id" in parameters:
                kwargs["speaker_id"] = self._speaker_id

            wav_parameter = next(
                (name for name in ("wav_file", "output_file") if name in parameters),
                None,
            )
            if wav_parameter:
                with wave.open(str(output_path), "wb") as wav_file:
                    result = synthesize(text, **{wav_parameter: wav_file}, **kwargs)
                    if result is not None and hasattr(result, "__iter__"):
                        for _ in result:
                            pass
                return output_path.stat().st_size > 44

            chunks = synthesize(text, **kwargs)
            self._write_audio_chunks(
                chunks,
                output_path,
                sentence_silence=self._settings["sentence_silence"],
            )
            return output_path.stat().st_size > 44
        except Exception as exc:
            self._python_api_failed = True
            self._voice = None
            logger.warning("Piper Python synthesis failed; using Piper CLI: %s", exc)
            return False

    def _make_synthesis_config(self) -> Any:
        try:
            from piper.config import SynthesisConfig
        except ImportError:
            return None
        try:
            parameters = inspect.signature(SynthesisConfig).parameters
            values = {
                key: self._settings[key]
                for key in ("length_scale", "noise_scale", "noise_w")
                if key in parameters
            }
            if self._speaker_id is not None and "speaker_id" in parameters:
                values["speaker_id"] = self._speaker_id
            if "sentence_silence" in parameters:
                values["sentence_silence"] = self._settings["sentence_silence"]
            return SynthesisConfig(**values)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _write_audio_chunks(
        chunks: Any,
        output_path: Path,
        sentence_silence: float = 0.0,
    ) -> None:
        iterator = iter(chunks)
        first = next(iterator, None)
        if first is None:
            raise RuntimeError("Piper returned no audio chunks")
        sample_rate = int(first.sample_rate)
        sample_width = int(getattr(first, "sample_width", 2))
        channels = int(getattr(first, "sample_channels", 1))
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            for chunk in itertools.chain((first,), iterator):
                wav_file.writeframes(chunk.audio_int16_bytes)
                if getattr(chunk, "is_final_chunk", False) and sentence_silence > 0:
                    silence_frames = int(sample_rate * sentence_silence)
                    wav_file.writeframes(
                        b"\x00" * silence_frames * channels * sample_width
                    )

    def _synthesize_with_cli(self, text: str, output_path: Path) -> bool:
        if not self._binary:
            return False
        command = [
            self._binary,
            "--model",
            self._model or "",
            "--output_file",
            str(output_path),
            "--length_scale",
            str(self._settings["length_scale"]),
            "--noise_scale",
            str(self._settings["noise_scale"]),
            "--noise_w",
            str(self._settings["noise_w"]),
            "--sentence_silence",
            str(self._settings["sentence_silence"]),
        ]
        if self._speaker_id is not None:
            command.extend(("--speaker", str(self._speaker_id)))
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            with self._process_lock:
                self._current_process = process
            _, stderr = process.communicate(
                input=(text + "\n").encode("utf-8"), timeout=60
            )
            if process.returncode:
                logger.error(
                    "Piper CLI exited with %d: %s",
                    process.returncode,
                    stderr.decode("utf-8", errors="replace").strip(),
                )
            return process.returncode == 0 and output_path.stat().st_size > 44
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("Could not synthesize with Piper CLI: %s", exc)
            if "process" in locals() and process.poll() is None:
                process.kill()
            return False
        finally:
            with self._process_lock:
                self._current_process = None

    def _prepare_wav(self, wav_path: Path) -> None:
        with wave.open(str(wav_path), "rb") as wav_file:
            params = wav_file.getparams()
            frames = wav_file.readframes(params.nframes)
        frame_width = params.sampwidth * params.nchannels
        silence = b"\x00" * int(
            params.framerate
            * self._settings["leading_silence_ms"]
            / 1000
            * frame_width
        )
        tail = b"\x00" * int(
            params.framerate
            * self._settings["trailing_silence_ms"]
            / 1000
            * frame_width
        )
        if params.sampwidth == 2 and self._settings["volume"] != 100:
            samples = array("h")
            samples.frombytes(frames)
            gain = self._settings["volume"] / 100.0
            samples = array("h", (int(sample * gain) for sample in samples))
            frames = samples.tobytes()
        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setparams(params)
            wav_file.writeframes(silence + frames + tail)

    def _refresh_cache_dir(self) -> None:
        self._cache_dir = None
        if not self._model or not self._model_config:
            return
        try:
            fingerprint = _cache_fingerprint(
                self._model,
                self._model_config,
                self._settings,
                self._speaker_id,
            )
        except OSError:
            return
        self._cache_dir = self._cache_root / fingerprint

    def _cache_path(self, character: Optional[str]) -> Optional[Path]:
        if not character or self._cache_dir is None:
            return None
        name = hashlib.sha256(character.encode("utf-8")).hexdigest()[:12]
        return self._cache_dir / f"{name}.wav"

    def _start_cache_generation(self) -> None:
        if not self.is_available():
            return
        if self._cache_worker and self._cache_worker.is_alive():
            return
        self._cache_worker = threading.Thread(
            target=self._generate_character_cache,
            daemon=True,
            name="piper-cache",
        )
        self._cache_worker.start()

    def _generate_character_cache(self) -> None:
        while self._cache_dir is not None:
            cache_dir = self._cache_dir
            for character, spoken_text in CHARACTER_PRONUNCIATIONS.items():
                if self._cache_dir != cache_dir:
                    break
                if self._queue.unfinished_tasks:
                    time.sleep(0.05)
                    continue
                target = cache_dir / (
                    f"{hashlib.sha256(character.encode('utf-8')).hexdigest()[:12]}.wav"
                )
                if target.is_file():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                fd, temp_name = tempfile.mkstemp(
                    prefix="brailce_cache_", suffix=".wav", dir=target.parent
                )
                os.close(fd)
                temp_path = Path(temp_name)
                try:
                    with self._synthesis_lock:
                        if self._cache_dir != cache_dir:
                            break
                        if not self._synthesize(spoken_text, temp_path):
                            logger.error(
                                "Piper could not create pronunciation cache for %r",
                                character,
                            )
                            continue
                        self._prepare_wav(temp_path)
                        if self._cache_dir == cache_dir:
                            os.replace(temp_path, target)
                except OSError:
                    logger.exception(
                        "Could not write pronunciation cache for %r", character
                    )
                finally:
                    temp_path.unlink(missing_ok=True)
            if self._cache_dir == cache_dir:
                return

    def wait_for_cache(self, timeout: Optional[float] = None) -> bool:
        """Wait for startup cache generation and report whether every entry exists."""
        worker = self._cache_worker
        if worker and worker.is_alive():
            worker.join(timeout=timeout)
        if worker and worker.is_alive():
            return False
        return all(
            (path := self._cache_path(character)) is not None and path.is_file()
            for character in CHARACTER_PRONUNCIATIONS
        )

    def availability_error(self) -> str:
        missing = []
        if not self._model or not Path(self._model).is_file():
            missing.append(f"Piper model (.onnx): {self._model or 'not configured'}")
        if not self._model_config or not Path(self._model_config).is_file():
            missing.append(
                f"Piper model config (.onnx.json): {self._model_config or 'not configured'}"
            )
        if not (
            (self._binary and Path(self._binary).is_file())
            or self._python_api_available()
        ):
            missing.append("Piper binary or piper-tts Python package")
        return "Piper speech is unavailable; " + "; ".join(missing)
