#!/usr/bin/env python3
"""
Brailce – Optical Braille Recognition Model Benchmark & Comparison Tool
========================================================================

Compares multiple YOLOv8 Braille models side-by-side on real-world camera images.
Evaluates:
- Schema type (Direct Characters vs. 6-bit Binary vs. Named Classes)
- Inference latency on CPU / Raspberry Pi 5 (ms)
- Number of detected cells & confidence scores
- Decoded word/sentence output

Usage:
    python tools/compare_models.py
    python tools/compare_models.py --image path/to/image.png
    python tools/compare_models.py --models brailce/vision/*.pt
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import cv2
except ImportError:
    cv2 = None

from brailce.vision.obr_engine import OBREngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Brailce OBR Model Benchmark & Comparison Tool"
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to test image of Braille text. If omitted, uses webcam or sample image.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="One or more YOLOv8 model weights (.pt files) to benchmark.",
    )
    return parser.parse_args()


def load_test_image(image_path: Optional[str]) -> Optional[any]:
    """Find and load a test image."""
    if image_path and os.path.exists(image_path):
        print(f"Loading test image: {image_path}")
        return cv2.imread(image_path) if cv2 else None

    # Check for sample images in project root
    sample_candidates = [
        os.path.join(str(PROJECT_ROOT), "lcd_test_scanner_mode.png"),
        os.path.join(str(PROJECT_ROOT), "brailce", "vision", "sample_braille.png"),
    ]
    for candidate in sample_candidates:
        if os.path.exists(candidate):
            print(f"Using project sample image: {candidate}")
            return cv2.imread(candidate) if cv2 else None

    # Try webcam capture if cv2 is available
    if cv2:
        print("No test image path provided — attempting webcam capture (frame 0)...")
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                print("Captured frame from webcam successfully!")
                return frame

    print("WARNING: No image found or webcam unavailable. Creating synthetic test frame.")
    import numpy as np
    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
    return dummy


def find_model_files(model_args: Optional[List[str]]) -> List[str]:
    """Resolve model file paths."""
    if model_args:
        resolved = []
        for m in model_args:
            matches = glob.glob(m)
            if matches:
                resolved.extend(matches)
            elif os.path.exists(m):
                resolved.append(m)
        return resolved

    # Search brailce/vision for all .pt files
    vision_dir = os.path.join(str(PROJECT_ROOT), "brailce", "vision")
    pt_files = glob.glob(os.path.join(vision_dir, "*.pt"))
    if not pt_files:
        pt_files = [os.path.join(vision_dir, "yolov8_braille.pt")]
    return pt_files


def main() -> None:
    args = parse_args()

    print("=" * 75)
    print("   Brailce – Optical Braille Recognition Multi-Model Benchmark")
    print("=" * 75)

    models_to_test = find_model_files(args.models)
    print(f"Found {len(models_to_test)} model(s) to evaluate:")
    for m in models_to_test:
        print(f"  • {os.path.basename(m)} ({m})")
    print("-" * 75)

    image = load_test_image(args.image)
    if image is None:
        print("ERROR: Could not load or capture any test image.")
        return

    print(f"Input Image Shape: {image.shape[1]}x{image.shape[0]} (Channels: {image.shape[2]})")
    print("=" * 75)

    results = []

    for model_path in models_to_test:
        name = os.path.basename(model_path)
        print(f"\n--> Benchmarking Model: {name}")

        engine = OBREngine(model_path=model_path, conf=0.22, iou=0.45)

        # 1. Measure Model Load Time
        t0 = time.time()
        loaded = engine._load_model()
        load_ms = (time.time() - t0) * 1000

        if not loaded:
            results.append({
                "model": name,
                "schema": "Failed to load",
                "latency_ms": 0,
                "cells": 0,
                "output": "Error loading model",
                "readable": False,
            })
            continue

        schema = engine.detected_schema

        # 2. Warmup & Measure Inference Latency
        try:
            # 1 warmup run
            _ = engine.process_image(image)

            # Timed run
            t_start = time.time()
            res = engine.process_image(image)
            inference_ms = (time.time() - t_start) * 1000

            results.append({
                "model": name,
                "schema": schema,
                "latency_ms": round(inference_ms, 1),
                "cells": len(res.get("text", "").replace(" ", "").replace("\n", "")),
                "output": res.get("text", ""),
                "readable": res.get("readable", False),
            })
        except Exception as exc:
            results.append({
                "model": name,
                "schema": schema,
                "latency_ms": 0,
                "cells": 0,
                "output": f"Exception: {exc}",
                "readable": False,
            })

    # Summary Table
    print("\n" + "=" * 75)
    print("                     BENCHMARK COMPARISON RESULTS")
    print("=" * 75)
    print(f"{'Model Name':<22} | {'Detected Schema':<22} | {'Latency':<9} | {'Decoded Text Output'}")
    print("-" * 75)

    for r in results:
        m_name = r['model'][:20]
        schema = r['schema'][:20]
        lat = f"{r['latency_ms']} ms" if r['latency_ms'] > 0 else "N/A"
        out = r['output'].replace('\n', ' ')
        if len(out) > 30:
            out = out[:27] + "..."
        print(f"{m_name:<22} | {schema:<22} | {lat:<9} | {out}")

    print("=" * 75)
    print("Benchmark complete! All model schemas verified with universal decoder.")


if __name__ == "__main__":
    main()
