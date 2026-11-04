"""Generate the configured Piper pronunciation cache on this machine."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brailce.config.loader import ConfigLoader
from brailce.speech.service import SpeechService


def main() -> int:
    config = ConfigLoader.load(str(PROJECT_ROOT / "brailce" / "config" / "config.json"))
    try:
        speech = SpeechService.from_config(config)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    engine = speech.piper_engine
    print(f"Generating Piper pronunciation cache for {engine.model_path}")
    wait_for_cache = getattr(engine, "wait_for_cache", None)
    if not callable(wait_for_cache) or not wait_for_cache(timeout=1800):
        print("Piper pronunciation cache generation did not finish.", file=sys.stderr)
        speech.shutdown()
        return 1
    print("Piper pronunciation cache is ready.")
    speech.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
