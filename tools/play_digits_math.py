import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess
import time

def say(text, scale="1.0"):
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

digits_and_math = [
    # Numbers
    ("number zero",  "0"),
    ("number one",   "1"),
    ("number two",   "2"),
    ("number three", "3"),
    ("number four",  "4"),
    ("number five",  "5"),
    ("number six",   "6"),
    ("number seven", "7"),
    ("number eight", "8"),
    ("number nine",  "9"),

    # Math
    ("plus sign",     "+"),
    ("minus",         "-"),
    ("multiplied by", "*"),
    ("divided by",    "/"),
    ("equals",        "="),
]

print("=== Playing digits 0-9 and math operators on Pi speaker ===")
for phrase, label in digits_and_math:
    print(f"Speaking: {label} -> '{phrase}'")
    say(phrase)
    time.sleep(0.35)

print("Finished digits and math test!")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/play_digits_math.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/play_digits_math.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print("ERR:", err)
ssh.close()
