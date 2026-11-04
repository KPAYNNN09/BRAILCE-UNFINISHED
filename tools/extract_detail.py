import cv2

cap = cv2.VideoCapture('video_360p.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)

for t in [204, 206, 208, 210]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f'frames_360p/detail_{t}s.jpg', frame)

cap.release()
print("Saved detail frames.")

