import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=5)

cmds = [
    ("PROCESSES", "ps aux | grep -E 'python|piper|main.py' | grep -v grep"),
    ("WAV FILES", "ls -la /home/raspberrypi5/brailce/brailce/audio/characters/ | head -n 20"),
    ("SPEECH SERVICE MOD TIME", "ls -l --full-time /home/raspberrypi5/brailce/brailce/speech/service.py /home/raspberrypi5/brailce/brailce/speech/piper_engine.py"),
    ("PYCACHE CHECK", "find /home/raspberrypi5/brailce -name '__pycache__'")
]

for label, cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(f"=== {label} ===")
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("STDERR:", err)

ssh.close()

