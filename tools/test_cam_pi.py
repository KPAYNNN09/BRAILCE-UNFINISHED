import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import sys
import os

if "/usr/lib/python3/dist-packages" not in sys.path:
    sys.path.append("/usr/lib/python3/dist-packages")

print("Checking picamera2 in sys.path with dist-packages added:")
try:
    import picamera2
    print("SUCCESS: picamera2 imported!")
    from picamera2 import Picamera2
    p = Picamera2()
    print("Picamera2 instantiated successfully!")
    cfg = p.create_preview_configuration(main={"size": (640, 480), "format": "BGR888"})
    p.configure(cfg)
    p.start()
    frame = p.capture_array("main")
    print(f"Captured REAL camera frame shape: {frame.shape}")
    p.stop()
    p.close()
    print("Picamera2 test complete!")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_cam.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('/home/raspberrypi5/brailce/venv/bin/python3 /home/raspberrypi5/test_cam.py')
print("=== STDOUT ===")
print(stdout.read().decode('utf-8', errors='replace'))
print("=== STDERR ===")
print(stderr.read().decode('utf-8', errors='replace'))
ssh.close()
