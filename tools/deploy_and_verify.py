import paramiko
import os

LOCAL_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

sftp = ssh.open_sftp()

files_to_sync = [
    "brailce/vision/camera.py",
    "brailce/vision/obr_engine.py",
    "brailce/speech/piper_engine.py",
    "brailce/modes/free_input.py",
    "brailce/modes/ai_assistant.py",
    "brailce/modes/scanner_mode.py",
    "brailce/config/config.json",
    "brailce/tests/test_free_input.py",
    "brailce/tests/test_ai.py",
]

for rel_path in files_to_sync:
    local_path = os.path.join(LOCAL_BASE, rel_path.replace("/", os.sep))
    remote_path = f"/home/raspberrypi5/brailce/{rel_path}"
    print(f"Uploading {rel_path} -> {remote_path}...")
    sftp.put(local_path, remote_path)

# Also ensure dist-packages.pth in venv
pth_target = "/home/raspberrypi5/brailce/venv/lib/python3.13/site-packages/dist-packages.pth"
with sftp.file(pth_target, "w") as f:
    f.write("/usr/lib/python3/dist-packages\n")
print(f"Wrote {pth_target}")

sftp.close()

# Run pytest on Pi
print("Running pytest on Raspberry Pi...")
stdin, stdout, stderr = ssh.exec_command("cd ~/brailce && ./venv/bin/pytest brailce/tests/test_free_input.py brailce/tests/test_ai.py")
print("=== PYTEST STDOUT ===")
print(stdout.read().decode('utf-8', errors='replace'))
print("=== PYTEST STDERR ===")
print(stderr.read().decode('utf-8', errors='replace'))

# Test camera initialization in Pi's venv
print("Testing Camera initialization in Pi's venv...")
test_cmd = """cd ~/brailce && ./venv/bin/python3 -c "
from brailce.vision.camera import PiCameraDevice
cam = PiCameraDevice()
print('Camera is_available:', cam.is_available(), 'init_error:', cam.init_error)
frame = cam.capture_image()
print('Frame captured successfully:', frame.shape if frame is not None else None)
cam.close()
" """
stdin, stdout, stderr = ssh.exec_command(test_cmd)
print("=== CAMERA STDOUT ===")
print(stdout.read().decode('utf-8', errors='replace'))
print("=== CAMERA STDERR ===")
print(stderr.read().decode('utf-8', errors='replace'))

ssh.close()
print("Deployment and verification complete!")
