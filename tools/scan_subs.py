import cv2
import os

cap = cv2.VideoCapture('video_360p.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)

# Let's sample frames every 3 seconds up to 300s
os.makedirs('sub_scans', exist_ok=True)
for t in range(0, 305, 3):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
    ret, frame = cap.read()
    if ret:
        h, w, _ = frame.shape
        sub_crop = frame[int(h*0.78):, :]
        cv2.imwrite(f"sub_scans/sub_{t:03d}s.jpg", sub_crop)

cap.release()
print("Saved 3-second interval subtitle crops.")

