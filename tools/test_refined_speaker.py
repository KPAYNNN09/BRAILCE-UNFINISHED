import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = r'''
import subprocess
import time

def play(text, scale="1.0"):
    cmd = ["echo", text]
    p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    piper = subprocess.Popen(
        ["/home/raspberrypi5/piper/piper/piper", "--model", "/home/raspberrypi5/piper/en_US-ryan-medium.onnx", "--output-raw", "--length-scale", scale],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    p1.stdout.close()
    aplay = subprocess.Popen(
        ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-q", "-"],
        stdin=piper.stdout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    piper.stdout.close()
    aplay.wait()
    piper.wait()

tests = [
    # 1. Letters (bare, no 'the letter')
    ("A.", "A"),
    ("Bee.", "B"),
    ("See.", "C"),
    ("Dee.", "D"),
    # M, N, S variants
    ("M.", "M as M."),
    ("N.", "N as N."),
    ("S.", "S as S."),
    # 2. Math
    ("plus.", "plus"),
    ("divided by.", "divided by"),
    ("multiplied by.", "multiplied by"),
    # 3. Punctuation
    ("dot.", "period as dot"),
    ("comma.", "comma"),
    # 4. Words
    ("cat.", "word cat"),
    ("dog.", "word dog"),
    ("hello.", "word hello"),
]

print("=== Playing refined characters and words on Pi speaker ===")
for text, label in tests:
    print(f"Playing {label}: '{text}'")
    play(text)
    time.sleep(0.35)

print("Finished!")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_refined.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_refined.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print("ERR:", err)
ssh.close()
