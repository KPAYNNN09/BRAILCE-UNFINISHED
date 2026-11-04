import os
import sys

import cv2
import numpy as np

img_path = os.environ.get("BRAILCE_TEST_IMAGE")
if not img_path or not os.path.isfile(img_path):
    raise SystemExit("Set BRAILCE_TEST_IMAGE to a valid image file path.")
img = cv2.imread(img_path)
if img is None:
    raise SystemExit(f"Could not read test image: {img_path}")

def enhance_braille(image):
    # Convert to LAB
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    # Apply CLAHE to L-channel
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced_lab = cv2.merge((cl, a, b))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

enhanced = enhance_braille(img)
cv2.imwrite("tools/enhanced_braille.jpg", enhanced)
print("Enhanced image saved!")
