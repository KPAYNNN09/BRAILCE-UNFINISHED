import cv2
import os

os.makedirs('video_frames', exist_ok=True)
cap = cv2.VideoCapture('video.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps
print(f"FPS: {fps}, Total frames: {total_frames}, Duration: {duration:.2f}s")

# Sample a frame every 15 seconds
timestamps = range(0, int(duration), 15)
for t in timestamps:
    frame_no = int(t * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f"video_frames/frame_{t:03d}s.jpg", frame)

print("Frames extracted.")
cap.release()

