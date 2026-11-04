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

say("Testing letter A pronunciations.", "1.0")
time.sleep(1.0)

candidates = [
    ("A.", "A dot"),
    ("eigh.", "eigh dot"),
    ("ay.", "ay dot"),
    ("eh.", "eh dot"),
]

for word, label in candidates:
    print(f"Playing {label} ({word})...")
    say(word, "1.35")
    time.sleep(1.2)

print("Done A test!")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_a_cand.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_a_cand.py')
out = stdout.read().decode('utf-8', errors='replace')
print(out)
ssh.close()
