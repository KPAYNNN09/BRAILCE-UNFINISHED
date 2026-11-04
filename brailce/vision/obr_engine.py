"""
Optical Braille Recognition (OBR) Engine
========================================

Universal multi-schema Braille recognition engine supporting:
1. Recommendation 1: "Braille" by braille sight (3.1k images, direct `#`, `A`..`Z`, `0`..`9`)
2. Recommendation 2: "Braille" by Prasarnmit demonstration school (1.56k images, 6-bit binary dots `000000`..`111111`)
3. Recommendation 3: "Braille Detection" by yapayzeka (1.32k images, real embossed letters `A`..`Z`)
4. Public Roboflow Uradela format (named classes `number_sign`, `capital`, `period`, etc.)
"""

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

try:
    import cv2
except ImportError:
    cv2 = None
import numpy as np

logger = logging.getLogger(__name__)


class OBREngine:
    """
    Universal engine for translating camera images of physical Braille into text.
    Automatically detects model schema and supports direct characters, 6-bit binary dot
    configurations, and named Roboflow classes.
    """

    # Schema 1: 6-bit Binary Dot Strings (Prasarnmit Demonstration School & DotNeuralNet)
    # bit 0 = dot 1, bit 1 = dot 2, ..., bit 5 = dot 6
    BINARY_DICT: Dict[str, str] = {
        # Standard Alphabet (A-Z)
        "100000": "A", "110000": "B", "100100": "C", "100110": "D", "100010": "E",
        "110100": "F", "110110": "G", "110010": "H", "010100": "I", "010110": "J",
        "101000": "K", "111000": "L", "101100": "M", "101110": "N", "101010": "O",
        "111100": "P", "111110": "Q", "111010": "R", "011100": "S", "011110": "T",
        "101001": "U", "111001": "V", "010111": "W", "101101": "X", "101111": "Y",
        "101011": "Z",
        # Single-dot and common punctuation
        "010000": ",", "011000": ";", "010010": ":", "010011": ".",
        "011010": "!", "011001": "?", "001000": "'", "001001": "-",
        "001101": "+", "011011": "=", "001011": "\"", "000100": "'",
        "000010": "E",  # Faint dot 1 on E
        "000110": "",  "000111": "_", "001010": "*",
        "001100": "/", "010001": "?", "010101": "W", "011101": "",
        "011111": "",  "100001": "U", "100011": "E", "100101": "X",
        "100111": "",  "110001": "H", "110011": "",  "110101": "",
        "110111": "",  "111011": "",  "111101": "",  "111111": "",
        # Common single-dot misses / contractions
        "001110": "N",
        # Indicators
        "000001": "^",  # Capital sign (Dot 6)
        "000101": "",   # Letter sign / italic prefix
        "001111": "#",  # Number sign (Dots 3,4,5,6)
        "000000": " "   # Blank / space cell
    }

    # Schema 2: Named Roboflow Dataset Class Labels (Uradela dataset)
    NAMED_DICT: Dict[str, str] = {
        "capital": "^",
        "cap": "^",
        "number_sign": "#",
        "number": "#",
        "num": "#",
        "hash": "#",
        "letter_sign": "",
        "period": ".",
        "comma": ",",
        "question_mark": "?",
        "question": "?",
        "exclamation_mark": "!",
        "exclamation": "!",
        "colon": ":",
        "semicolon": ";",
        "hyphen": "-",
        "dash": "-",
        "apostrophe": "'",
        "openquotation": "\"",
        "closequotation": "\"",
        "quote": "\"",
        "parenthesis": "(",
        "open_parenthesis": "(",
        "close_parenthesis": ")",
        "asterisk": "*",
        "ampersand": "&",
        "plus": "+",
        "minus": "-",
        "equals": "=",
        "slash": "/"
    }

    # Schema 3: Direct Symbols & Punctuation (braille sight & yapayzeka datasets)
    DIRECT_SYMBOLS: Dict[str, str] = {
        "#": "#",
        "^": "^",
        ".": ".",
        ",": ",",
        "?": "?",
        "!": "!",
        "-": "-",
        "'": "'",
        "\"": "\"",
        ":": ":",
        ";": ";",
        "+": "+",
        "*": "*",
        "/": "/",
        "=": "=",
        "(": "(",
        ")": ")"
    }

    NUM_MAP: Dict[str, str] = {
        "A": "1", "B": "2", "C": "3", "D": "4", "E": "5",
        "F": "6", "G": "7", "H": "8", "I": "9", "J": "0"
    }

    def __init__(
        self,
        model_path: str = "brailce/vision/yolov8_braille.pt",
        conf: float = 0.22,
        iou: float = 0.45
    ) -> None:
        self.model_path = model_path
        self.conf = conf
        self.iou = iou
        self._model = None
        self.detected_schema = "uninitialized"

    def _load_model(self) -> bool:
        if self._model is not None:
            return True

        import os
        if not os.path.exists(self.model_path):
            logger.info("OBR Model not found at %s. Attempting to download default weights...", self.model_path)
            try:
                import urllib.request
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                url = "https://github.com/snoop2head/DotNeuralNet/raw/main/weights/yolov8_braille.pt"
                print(f"\n[OBR] Downloading YOLOv8 Braille weights (49 MB) to {self.model_path}...")
                urllib.request.urlretrieve(url, self.model_path)
                print("[OBR] Download complete!\n")
            except Exception as exc:
                logger.error("Could not download YOLO model: %s", exc)
                return False

        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
            self.detected_schema = self._detect_model_schema()
            logger.info("OBR Engine: Loaded '%s' (Detected Schema: %s)", self.model_path, self.detected_schema)
            return True
        except ImportError:
            logger.error("ultralytics package is not installed. Please run: pip install ultralytics")
            return False

    def _detect_model_schema(self) -> str:
        """Inspect model class names to identify the training dataset schema."""
        if not self._model or not hasattr(self._model, "names") or not self._model.names:
            return "universal"

        names = list(self._model.names.values())
        str_names = [str(n).strip() for n in names]

        # 1. Check for 6-bit binary strings (Prasarnmit Demonstration School / DotNeuralNet)
        binary_matches = sum(1 for n in str_names if len(n) == 6 and set(n).issubset({"0", "1"}))
        if binary_matches >= min(5, len(str_names)):
            return "binary_dots (Prasarnmit / DotNeuralNet)"

        # 2. Check for direct character/symbol labels (braille sight / yapayzeka)
        if any(n in {"#", "^"} for n in str_names) or (any(len(n) == 1 and n.isalpha() for n in str_names) and any(n in {".", ",", "!"} for n in str_names)):
            return "direct_characters (braille sight / yapayzeka)"

        # 3. Check for named classes (Uradela dataset)
        if any(n.lower() in {"number_sign", "capital", "period"} for n in str_names):
            return "named_classes (Uradela)"

        return "universal_hybrid"

    @classmethod
    def decode_cell_label(cls, raw_name: str) -> str:
        """
        Universal single-cell Braille label decoder.
        Supports:
        1. 6-bit Binary Dot Strings ("100000" -> "A", "001111" -> "#")
        2. Direct Symbol & Character Labels ("#", "^", "A".."Z", "0".."9", ".", ",")
        3. Roboflow Named Class Labels ("number_sign", "capital", "period")
        """
        clean_name = str(raw_name).strip()
        # Strip plural 's' suffix sometimes added by summary tools
        if len(clean_name) > 1 and not clean_name.isdigit():
            clean_name = clean_name.rstrip("sS").strip()

        # 1. Direct symbol check (handles '#' and '^' from braille sight)
        if clean_name in cls.DIRECT_SYMBOLS:
            return cls.DIRECT_SYMBOLS[clean_name]

        # 2. 6-bit binary format (Prasarnmit & DotNeuralNet)
        if clean_name in cls.BINARY_DICT:
            return cls.BINARY_DICT[clean_name]

        # 3. Roboflow named format (Uradela)
        lower_name = clean_name.lower()
        if lower_name in cls.NAMED_DICT:
            return cls.NAMED_DICT[lower_name]

        # 4. Prefixed format (e.g. "letter_A", "char_B")
        for prefix in ("letter_", "char_", "digit_"):
            if lower_name.startswith(prefix):
                remainder = clean_name[len(prefix):]
                if remainder.isalpha():
                    return remainder.upper()
                if remainder.isdigit():
                    return remainder

        # 5. Direct single-letter or digit (yapayzeka & braille sight)
        if len(clean_name) == 1 and clean_name.isalpha():
            return clean_name.upper()
        if clean_name.isdigit():
            return clean_name

        return ""

    @classmethod
    def filter_valid_detections(cls, boxes_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate candidate Braille detections to prevent camera sensor noise from triggering false positives:
        1. Aspect ratio / circularity: min(w, h) / max(w, h) >= 0.65
        2. Radius/size consistency: size within 35% of median size
        3. Grid alignment: at least 3 valid detections aligned along rows or columns in a Braille grid
        """
        if not boxes_data or len(boxes_data) < 3:
            return []

        # 1. Circularity / aspect ratio check (circularity >= 0.65)
        circular = []
        for b in boxes_data:
            w, h = b["w"], b["h"]
            aspect = min(w, h) / max(1e-6, max(w, h))
            if aspect >= 0.65:
                circular.append(b)

        if len(circular) < 3:
            return []

        # 2. Consistent radius / size (within 35% of median)
        sizes = [(b["w"] + b["h"]) / 2.0 for b in circular]
        median_s = float(np.median(sizes))
        if median_s <= 0:
            return []

        consistent = []
        for b in circular:
            s = (b["w"] + b["h"]) / 2.0
            if abs(s - median_s) / median_s <= 0.35:
                consistent.append(b)

        if len(consistent) < 3:
            return []

        # 3. Braille grid alignment check:
        # Require at least 3 consistent dots aligned in a grid (e.g. shared row or column or multi-cell layout)
        sorted_y = sorted(consistent, key=lambda b: b["y"])
        rows: List[List[Dict[str, Any]]] = []
        for b in sorted_y:
            placed = False
            for r in rows:
                if abs(b["y"] - np.mean([item["y"] for item in r])) <= (median_s * 0.70):
                    r.append(b)
                    placed = True
                    break
            if not placed:
                rows.append([b])

        sorted_x = sorted(consistent, key=lambda b: b["x"])
        cols: List[List[Dict[str, Any]]] = []
        for b in sorted_x:
            placed = False
            for c in cols:
                if abs(b["x"] - np.mean([item["x"] for item in c])) <= (median_s * 0.70):
                    c.append(b)
                    placed = True
                    break
            if not placed:
                cols.append([b])

        has_row_aligned = any(len(r) >= 3 for r in rows)
        has_col_aligned = any(len(c) >= 3 for c in cols)
        has_grid = (len(rows) >= 2 and any(len(r) >= 2 for r in rows)) or (len(cols) >= 2 and any(len(c) >= 2 for c in cols))

        if not (has_row_aligned or has_col_aligned or has_grid):
            return []

        return consistent

    @classmethod
    def decode_boxes(cls, boxes_data: List[Dict[str, Any]], space_threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        Process bounding box data, perform adaptive line clustering, horizontal sorting,
        word space reconstruction, and Grade 1 indicator translation.
        """
        valid_boxes = cls.filter_valid_detections(boxes_data)
        if not valid_boxes or len(valid_boxes) < 3:
            return {"readable": False, "text": "No Braille detected. Please adjust the sheet."}

        # 1. Adaptive sizing
        widths = [b["w"] for b in valid_boxes]
        heights = [b["h"] for b in valid_boxes]
        median_w = float(np.median(widths)) if widths else 30.0
        median_h = float(np.median(heights)) if heights else 40.0

        if space_threshold is None:
            space_threshold = max(20.0, median_w * 1.30)

        # 2. Robust vertical line clustering (handles tilted paper)
        sorted_by_y = sorted(valid_boxes, key=lambda b: b["y"])
        lines: List[List[Dict[str, Any]]] = []

        for b in sorted_by_y:
            b_top = b["y"] - b["h"] / 2.0
            b_bot = b["y"] + b["h"] / 2.0

            best_line = None
            max_overlap = 0.0
            for line in lines:
                line_top = min(item["y"] - item["h"] / 2.0 for item in line)
                line_bot = max(item["y"] + item["h"] / 2.0 for item in line)
                line_h = max(item["h"] for item in line)

                overlap = max(0.0, min(b_bot, line_bot) - max(b_top, line_top))
                if overlap > (line_h * 0.35) and overlap > max_overlap:
                    max_overlap = overlap
                    best_line = line

            if best_line is not None:
                best_line.append(b)
            else:
                lines.append([b])

        # Sort lines top-to-bottom by median Y
        lines.sort(key=lambda l: float(np.median([item["y"] for item in l])))

        # 3. Sort horizontally & deduplicate ghost detections
        cleaned_lines: List[List[Dict[str, Any]]] = []
        for line in lines:
            line.sort(key=lambda b: b["x"])
            dedup: List[Dict[str, Any]] = []
            for b in line:
                if not dedup:
                    dedup.append(b)
                elif abs(b["x"] - dedup[-1]["x"]) < (median_w * 0.65):
                    if b.get("conf", 0) > dedup[-1].get("conf", 0):
                        dedup[-1] = b
                else:
                    dedup.append(b)
            if dedup:
                cleaned_lines.append(dedup)

        # 4. Translate Braille tokens into full text with spaces, numbers, and capitals
        line_strings: List[str] = []

        for line in cleaned_lines:
            line_str = ""
            is_number = False
            is_capital = False
            last_x = None

            for b in line:
                # Inter-cell distance for word spacing
                if last_x is not None and (b["x"] - last_x) > space_threshold:
                    line_str += " "
                    is_number = False
                    is_capital = False
                last_x = b["x"]

                char = cls.decode_cell_label(b.get("name", ""))

                # State machine triggers
                if char == "#":
                    is_number = True
                    continue
                if char == "^":
                    is_capital = True
                    continue
                if char == "":
                    continue

                if is_number:
                    if char in cls.NUM_MAP:
                        line_str += cls.NUM_MAP[char]
                    elif char.isdigit():
                        line_str += char
                    elif char in {".", ","}:
                        line_str += char
                    else:
                        is_number = False
                        line_str += char
                else:
                    if is_capital and char.isalpha():
                        line_str += char.upper()
                        is_capital = False
                    else:
                        line_str += char

            clean_l = " ".join(line_str.split()).strip()
            if clean_l:
                line_strings.append(clean_l)

        final_text = " \n ".join(line_strings).strip()
        if not final_text:
            return {"readable": False, "text": "No Braille detected. Please adjust the sheet."}

        logger.info("Decoded text: %s", final_text)
        return {"readable": True, "text": final_text}

    @staticmethod
    def enhance_contrast(image: np.ndarray) -> np.ndarray:
        """
        Enhance shadow contrast for embossed physical Braille paper
        using Contrast Limited Adaptive Histogram Equalization (CLAHE).
        """
        if image is None or cv2 is None:
            return image
        try:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            enhanced_lab = cv2.merge((cl, a, b))
            return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        except Exception:
            return image

    @staticmethod
    def has_paper_background(image: np.ndarray) -> bool:
        """
        Verify that a physical paper sheet with actual contrast exists in the frame.
        Prevents dark camera sensor noise from being amplified by CLAHE into false Braille dots.
        Paper & Contrast Gate:
        - Real paper under illumination must have brightness: np.percentile(gray, 85) > 95
        - Real embossed dots and paper under illumination must have local shadow contrast: np.percentile(gray, 95) - np.percentile(gray, 5) > 40
        """
        if image is None or image.size == 0:
            return False
        try:
            if cv2 is not None and len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif len(image.shape) == 3:
                gray = np.mean(image, axis=2).astype(np.uint8)
            else:
                gray = image

            p85 = float(np.percentile(gray, 85))
            if p85 <= 95.0:
                return False

            p95 = float(np.percentile(gray, 95))
            p5 = float(np.percentile(gray, 5))
            if (p95 - p5) <= 40.0:
                return False

            return True
        except Exception:
            return False

    @staticmethod
    def _extract_boxes(results: Any) -> List[Dict[str, Any]]:
        """Extract bounding box coordinate dictionaries from YOLO results."""
        boxes_data = []
        if not results:
            return boxes_data
        for result in results:
            if not hasattr(result, "boxes") or result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                class_id = int(box.cls[0])
                class_name = str(result.names[class_id])
                conf = float(box.conf[0])
                boxes_data.append({
                    "x": (x1 + x2) / 2.0,
                    "y": (y1 + y2) / 2.0,
                    "w": abs(x2 - x1),
                    "h": abs(y2 - y1),
                    "name": class_name,
                    "conf": conf
                })
        return boxes_data

    def detect_braille_presence(self, image: np.ndarray) -> bool:
        """Fast check if valid Braille cells are visible in the viewfinder."""
        if image is None or not self.has_paper_background(image) or not self._load_model():
            return False
        try:
            enhanced = self.enhance_contrast(image)
            results = self._model(enhanced, conf=self.conf, verbose=False)
            boxes_data = self._extract_boxes(results)
            valid = self.filter_valid_detections(boxes_data)
            if len(valid) >= 3:
                return True

            # Fallback check on raw frame
            results_raw = self._model(image, conf=self.conf, verbose=False)
            boxes_data_raw = self._extract_boxes(results_raw)
            valid_raw = self.filter_valid_detections(boxes_data_raw)
            if len(valid_raw) >= 3:
                return True
        except Exception as exc:
            logger.debug("detect_braille_presence error: %s", exc)
        return False

    def process_image(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Analyze an image, extract Braille cells using YOLOv8, decode them,
        and return a dictionary with status and text.
        """
        if image is None:
            return {"readable": False, "text": "Error: No image provided."}

        if not self.has_paper_background(image):
            logger.info("No paper background detected in image (low contrast or dark).")
            return {"readable": False, "text": "No Braille detected. Please adjust the sheet."}

        if not self._load_model():
            import os
            if not os.path.exists(self.model_path):
                return {"readable": False, "text": "Error: Model file missing."}
            try:
                import ultralytics
            except ImportError:
                return {"readable": False, "text": "Error: Run 'pip install ultralytics'"}
            return {"readable": False, "text": "Error: ML model could not be loaded."}

        logger.info("Starting Optical Braille Recognition with %s...", self.model_path)

        # 1. Dual-pass inference: Try CLAHE contrast-enhanced image first, then raw image
        enhanced = self.enhance_contrast(image)
        results = self._model(enhanced, conf=self.conf, iou=self.iou, verbose=False)
        boxes_data = self._extract_boxes(results)
        valid_boxes = self.filter_valid_detections(boxes_data)

        if len(valid_boxes) < 3:
            # Fallback pass on raw image
            results_raw = self._model(image, conf=self.conf, iou=self.iou, verbose=False)
            boxes_data_raw = self._extract_boxes(results_raw)
            valid_raw = self.filter_valid_detections(boxes_data_raw)
            if len(valid_raw) >= len(valid_boxes):
                boxes_data = boxes_data_raw

        return self.decode_boxes(boxes_data)

