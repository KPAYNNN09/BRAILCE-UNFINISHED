import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

# Test carrier sentence approach vs bare words
script = '''
import subprocess
import time

def say(text, scale="1.0"):
    cmd = ["echo", text]
    p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    piper = subprocess.Popen(["/home/raspberrypi5/piper/piper/piper", "--model", "/home/raspberrypi5/piper/en_US-ryan-medium.onnx", "--output-raw", "--length-scale", scale], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    p1.stdout.close()
    aplay = subprocess.Popen(["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-q", "-"], stdin=piper.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    piper.stdout.close()
    aplay.wait()
    piper.wait()

# Test A through H with carrier phrase "the letter X"
carrier_words = [
    ("the letter ay",    "A as: the letter ay"),
    ("the letter bee",   "B as: the letter bee"),
    ("the letter see",   "C as: the letter see"),
    ("the letter dee",   "D as: the letter dee"),
    ("the letter ee",    "E as: the letter ee"),
    ("the letter ef",    "F as: the letter ef"),
    ("the letter jee",   "G as: the letter jee"),
    ("the letter aitch", "H as: the letter aitch"),
    ("Jay",              "J as: Jay"),
]

print("Testing carrier phrase approach...")
for word, label in carrier_words:
    print(f"Playing: {label}")
    say(word)
    time.sleep(0.7)

print("Finished!")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_carrier.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_carrier.py')
out = stdout.read().decode('utf-8', errors='replace')
print(out)
ssh.close()
