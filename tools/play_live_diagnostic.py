import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess
import time

def say(text, scale="1.35"):
    cmd = f"echo '{text}' | /home/raspberrypi5/piper/piper/piper --model /home/raspberrypi5/piper/en_US-ryan-medium.onnx --output-raw --length-scale {scale} | aplay -r 22050 -f S16_LE -t raw -q -"
    subprocess.run(cmd, shell=True)

# 1. J at relaxed speed
say("Testing relaxed J.")
time.sleep(0.4)
say("Jay.", "1.4")
time.sleep(0.8)

# 2. Real English words for B, C, D, F, G, H
say("Testing real English words for letters.")
time.sleep(0.4)

words = [
    ("bee.", "B as bee"),
    ("sea.", "C as sea"),
    ("dee.", "D as dee"),
    ("ee.",  "E as ee"),
    ("ef.",  "F as ef"),
    ("gee.", "G as gee"),
    ("aitch.", "H as aitch"),
]

for word, label in words:
    print(f"Playing {label}...")
    say(word, "1.4")
    time.sleep(0.8)

say("Finished diagnostic test.")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/play_live_diag.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/play_live_diag.py')
out = stdout.read().decode('utf-8', errors='replace')
print(out)
ssh.close()
