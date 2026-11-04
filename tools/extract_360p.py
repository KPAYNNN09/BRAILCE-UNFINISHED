import cv2
import os

os.makedirs('frames_360p', exist_ok=True)
cap = cv2.VideoCapture('video_360p.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps
print(f"FPS: {fps}, Total frames: {total_frames}, Duration: {duration:.2f}s")

# Let's save a frame every 10 seconds, plus crop the bottom 25% where subtitles are
for t in range(0, int(duration), 10):
    frame_no = int(t * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f"frames_360p/full_{t:03d}s.jpg", frame)
        h, w, _ = frame.shape
        sub_crop = frame[int(h*0.75):, :]
        cv2.imwrite(f"frames_360p/sub_{t:03d}s.jpg", sub_crop)

print("Extracted 360p frames and subtitle crops.")
cap.release()

