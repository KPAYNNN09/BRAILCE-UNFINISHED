import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

tests = [
    # Digits
    ("number zero", "0_phrase"),
    ("zero", "0_bare"),
    ("number one", "1_phrase"),
    ("one", "1_bare"),
    ("number two", "2_phrase"),
    ("two", "2_bare"),
    ("number three", "3_phrase"),
    ("three", "3_bare"),
    ("number four", "4_phrase"),
    ("four", "4_bare"),
    ("number five", "5_phrase"),
    ("five", "5_bare"),
    ("number six", "6_phrase"),
    ("six", "6_bare"),
    ("seven", "7_bare"),
    ("number eight", "8_phrase"),
    ("eight", "8_bare"),
    ("nine", "9_bare"),

    # Math
    ("plus", "plus_bare"),
    ("plus sign", "plus_phrase"),
    ("minus", "minus_bare"),
    ("times", "times_bare"),
    ("multiplied by", "times_mult"),
    ("divided by", "div_bare"),
    ("equals", "equals_bare"),

    # Punctuation
    ("period", "period"),
    ("comma", "comma"),
    ("question mark", "question"),
    ("exclamation mark", "exclamation"),
    ("apostrophe", "apostrophe"),
    ("quotation mark", "quote_phrase"),
    ("colon", "colon"),
    ("semicolon", "semicolon"),
    ("number sign", "hash"),
]

for text, label in tests:
    p2 = subprocess.Popen(['espeak-ng', '-v', 'en-us', '-q', '--ipa', text], stdout=subprocess.PIPE)
    ipa = p2.communicate()[0].decode().strip()
    
    cmd = ['/home/raspberrypi5/piper/piper/piper', '--model', '/home/raspberrypi5/piper/en_US-ryan-medium.onnx', '--output-raw']
    p_pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw, _ = p_pipe.communicate(input=(text + '\\n').encode())
    dur = len(raw) / (22050 * 2)
    print(f"{label:15} | {text:20} | ipa: {ipa:35} | dur: {dur:.2f}s")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_digits_math.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_digits_math.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print("ERR:", err)
ssh.close()
