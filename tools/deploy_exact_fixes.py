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
    "brailce/modes/free_input.py",
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

# 3. Kill any running Brailce processes so user has clean PuTTY terminal
print("Killing any running Brailce, piper, or aplay processes...")
ssh.exec_command("pkill -9 -f 'python3.*brailce' 2>/dev/null; pkill -9 -f piper 2>/dev/null; pkill -9 -f aplay 2>/dev/null")
time.sleep(1)

stdin, stdout, stderr = ssh.exec_command("ps aux | grep -i brailce | grep -v grep")
out = stdout.read().decode('utf-8', errors='replace').strip()
if out:
    print("Warning, still running:\n", out)
else:
    print("ALL processes stopped! Pi is 100% ready for manual test in PuTTY.")

ssh.close()
print("Deployment completed!")
