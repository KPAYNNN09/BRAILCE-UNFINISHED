import paramiko
import os
import time

LOCAL_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PI_HOST = "192.168.0.107"
PI_USER = "raspberrypi5"

print("Connecting to Raspberry Pi 5...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(PI_HOST, username=PI_USER, timeout=10)
print("Connected!")

# 1. Sync updated files
sftp = ssh.open_sftp()
files_to_sync = [
    "brailce/speech/piper_engine.py",
    "brailce/braille/mappings/letters.json",
]

for rel_path in files_to_sync:
    local_path = os.path.join(LOCAL_BASE, rel_path.replace("/", os.sep))
    remote_path = f"/home/raspberrypi5/brailce/{rel_path}"
    print(f"Uploading {rel_path} -> {remote_path}...")
    sftp.put(local_path, remote_path)

sftp.close()
print("Files synced successfully.")

# 2. Clear remote __pycache__
stdin, stdout, stderr = ssh.exec_command("find /home/raspberrypi5/brailce -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null")
stdout.read()

# 3. Test piper_engine directly inside Pi's venv
test_code = """
import sys
sys.path.insert(0, '/home/raspberrypi5/brailce')
from brailce.speech.piper_engine import PiperEngine

engine = PiperEngine()
print('Piper Engine available:', engine.is_available())
print('Testing speak A...')
engine.speak('A')
"""

stdin, stdout, stderr = ssh.exec_command(f"/home/raspberrypi5/brailce/venv/bin/python3 -c \"{test_code}\"")
print("=== Pi Engine Test ===")
print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print("ERR:", err)

# 4. Restart Brailce process cleanly
print("\nKilling any running Brailce/piper instances...")
ssh.exec_command("pkill -9 -f 'python3.*brailce' 2>/dev/null; pkill -9 -f piper 2>/dev/null; pkill -9 -f aplay 2>/dev/null")
time.sleep(1)

print("Starting Brailce in background...")
ssh.exec_command("cd ~/brailce && nohup ./venv/bin/python3 -m brailce > /tmp/brailce.log 2>&1 &")
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command("ps aux | grep -i brailce | grep -v grep")
out = stdout.read().decode('utf-8', errors='replace').strip()
if out:
    print("Brailce is RUNNING:\n", out)
else:
    print("WARNING: Brailce not found in ps! Check /tmp/brailce.log:")
    _, log_out, _ = ssh.exec_command("tail -25 /tmp/brailce.log")
    print(log_out.read().decode('utf-8', errors='replace'))

ssh.close()
print("Deployment completed successfully!")
