import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess
import time

def say(text, scale):
    cmd = f"echo '{text}' | /home/raspberrypi5/piper/piper/piper --model /home/raspberrypi5/piper/en_US-ryan-medium.onnx --output-raw --length-scale {scale} | aplay -r 22050 -f S16_LE -t raw -q -"
    subprocess.run(cmd, shell=True)

say("Testing J at different speeds.", "1.0")
time.sleep(1.0)

for scale in ["1.0", "1.25", "1.45", "1.65"]:
    print(f"Playing J at scale {scale}...")
    say("Jay.", scale)
    time.sleep(1.2)

print("Done J test!")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_j.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_j.py')
out = stdout.read().decode('utf-8', errors='replace')
print(out)
ssh.close()
