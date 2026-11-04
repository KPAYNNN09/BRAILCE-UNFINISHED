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

# Sequence to test on the speaker:
# 1. Letter A (the fix: "the letter A" -> IPA /eI/)
# 2. Letter I ("the letter eye" -> IPA /aI/)
# 3. Letters K through Z
letters_to_play = [
    ("the letter A",          "A (fixed to /eI/)"),
    ("the letter eye",        "I"),
    ("the letter kay",        "K"),
    ("the letter ell",        "L"),
    ("the letter em",         "M"),
    ("the letter en",         "N"),
    ("the letter oh",         "O"),
    ("the letter pee",        "P"),
    ("the letter cue",        "Q"),
    ("the letter ar",         "R"),
    ("the letter ess",        "S"),
    ("the letter tee",        "T"),
    ("the letter you",        "U"),
    ("the letter vee",        "V"),
    ("the letter double you", "W"),
    ("the letter ex",         "X"),
    ("the letter why",        "Y"),
    ("the letter zee",        "Z"),
]

print("=== Playing letter A, letter I, and letters K through Z on Pi speaker ===")
for phrase, label in letters_to_play:
    print(f"Speaking: {label} -> '{phrase}'")
    say(phrase)
    time.sleep(0.4)

print("Finished letters test!")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/play_remaining_letters.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/play_remaining_letters.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print("ERR:", err)
ssh.close()
