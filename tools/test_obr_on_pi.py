import os
import paramiko

local_image = os.environ.get("BRAILCE_TEST_IMAGE")
if not local_image or not os.path.isfile(local_image):
    raise SystemExit("Set BRAILCE_TEST_IMAGE to a valid local image file path.")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

sftp = ssh.open_sftp()
sftp.put(local_image, '/home/raspberrypi5/test_poem.png')
sftp.close()

test_script = '''
import sys
sys.path.insert(0, '/home/raspberrypi5/brailce')
import cv2
from brailce.vision.obr_engine import OBREngine

img = cv2.imread('/home/raspberrypi5/test_poem.png')
print('Image loaded on Pi:', img.shape)
eng = OBREngine(model_path='brailce/vision/yolov8_braille.pt', conf=0.16)
res = eng.process_image(img)
print('PI OBR RESULT:', res.get('readable'), 'Characters decoded:', len(res.get('text', '')))
print('Preview of translated text on Pi:')
print(res.get('text', '')[:250])
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/run_obr_test.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd ~/brailce && ./venv/bin/python3 /home/raspberrypi5/run_obr_test.py')
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))
ssh.close()
