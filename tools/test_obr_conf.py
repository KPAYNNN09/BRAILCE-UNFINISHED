import os
import sys
sys.path.insert(0, ".")
import cv2
from brailce.vision.obr_engine import OBREngine

img_path = os.environ.get("BRAILCE_TEST_IMAGE")
if not img_path or not os.path.isfile(img_path):
    raise SystemExit("Set BRAILCE_TEST_IMAGE to a valid image file path.")
img = cv2.imread(img_path)
if img is None:
    raise SystemExit(f"Could not read test image: {img_path}")

for conf in [0.25, 0.22, 0.18, 0.15, 0.12, 0.08]:
    engine = OBREngine(model_path='brailce/vision/yolov8_braille.pt', conf=conf)
    res = engine.process_image(img)
    readable = res.get("readable")
    txt = res.get("text", "")
    print(f"conf={conf:.2f} -> readable={readable}, length={len(txt)}, sample={repr(txt[:60])}")
