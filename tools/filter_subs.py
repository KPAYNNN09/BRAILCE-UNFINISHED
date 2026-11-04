import cv2
import numpy as np
import glob
import os

files = sorted(glob.glob('sub_scans/sub_*.jpg'))
prev = None
significant_changes = []

for f in files:
    img = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
    # Threshold for white text (intensity > 210)
    white_pixels = np.sum(img > 215)
    if white_pixels > 200: # Has text
        significant_changes.append((f, white_pixels))

print(f"Total candidate text frames: {len(significant_changes)}")
# Print sample candidates every few steps
selected = []
last_t = -100
for path, wp in significant_changes:
    # extract second
    t = int(path.split('_')[-1].replace('s.jpg', ''))
    if t - last_t >= 6:
        selected.append((t, path))
        last_t = t

print("Selected timestamps:", [s[0] for s in selected])

