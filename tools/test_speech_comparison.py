import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

# We will test speaking:
# A., B., C., D., E., F., G., H., W., J.
# with length-scale 1.35 on the Pi speaker
script = '''
import subprocess
import time

test_letters = [
    ("A.", "A dot"),
    ("B.", "B dot"),
    ("C.", "C dot"),
    ("D.", "D dot"),
    ("E.", "E dot"),
    ("F.", "F dot"),
    ("G.", "G dot"),
    ("H.", "H dot"),
    ("J.", "J dot"),
    ("W.", "W dot"),
    ("7.", "7 dot"),
    ("9.", "9 dot"),
    ("minus.", "minus dot"),
]

for text, label in test_letters:
    print(f"Playing: {label} ({text}) at length-scale 1.35...")
    cmd = f"echo '{text}' | /home/raspberrypi5/piper/piper/piper --model /home/raspberrypi5/piper/en_US-ryan-medium.onnx --output-raw --length-scale 1.35 | aplay -r 22050 -f S16_LE -t raw -q -"
    subprocess.run(cmd, shell=True)
    time.sleep(0.3)

print("Done playing test letters!")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_letters_play.py', 'w') as f:
    f.write(script)
sftp.close()

print("Running test on Pi speaker...")
stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_letters_play.py')
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print("OUT:\n", out)
if err:
    print("ERR:\n", err)
ssh.close()
