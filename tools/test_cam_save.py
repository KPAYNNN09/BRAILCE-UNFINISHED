import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import sys
import os

if "/usr/lib/python3/dist-packages" not in sys.path:
    sys.path.append("/usr/lib/python3/dist-packages")

from picamera2 import Picamera2
import cv2

p = Picamera2()
cfg = p.create_preview_configuration(main={"size": (1280, 960), "format": "BGR888"})
p.configure(cfg)
p.start()
img = p.capture_array("main")
cv2.imwrite("/home/raspberrypi5/test_real_cam_1280.jpg", img)
p.stop()
p.close()
print("SUCCESS: captured 1280x960 frame:", img.shape)
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_cam_save.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('/home/raspberrypi5/brailce/venv/bin/python3 /home/raspberrypi5/test_cam_save.py')
print("STDOUT:", stdout.read().decode('utf-8', errors='replace'))
print("STDERR:", stderr.read().decode('utf-8', errors='replace'))
ssh.close()
