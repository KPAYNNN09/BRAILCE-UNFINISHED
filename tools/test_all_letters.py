import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

# Let's test letters K through Z and others with "the letter X"
tests = [
    # Letters
    ("the letter A", "A"),
    ("the letter bee", "B"),
    ("the letter see", "C"),
    ("the letter dee", "D"),
    ("the letter ee", "E"),
    ("the letter ef", "F"),
    ("the letter jee", "G"),
    ("the letter aitch", "H"),
    ("the letter eye", "I"),
    ("the letter jay", "J"),
    ("the letter kay", "K"),
    ("the letter ell", "L"),
    ("the letter em", "M"),
    ("the letter en", "N"),
    ("the letter oh", "O"),
    ("the letter pee", "P"),
    ("the letter cue", "Q"),
    ("the letter ar", "R"),
    ("the letter are", "R_are"),
    ("the letter ess", "S"),
    ("the letter tee", "T"),
    ("the letter you", "U"),
    ("the letter vee", "V"),
    ("the letter double you", "W"),
    ("Double you", "W_bare"),
    ("the letter ex", "X"),
    ("the letter why", "Y"),
    ("the letter zee", "Z"),
]

for text, label in tests:
    p2 = subprocess.Popen(['espeak-ng', '-v', 'en-us', '-q', '--ipa', text], stdout=subprocess.PIPE)
    ipa = p2.communicate()[0].decode().strip()
    
    cmd = ['/home/raspberrypi5/piper/piper/piper', '--model', '/home/raspberrypi5/piper/en_US-ryan-medium.onnx', '--output-raw']
    p_pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw, _ = p_pipe.communicate(input=(text + '\\n').encode())
    dur = len(raw) / (22050 * 2)
    print(f"{label:10} | {text:25} | ipa: {ipa:35} | dur: {dur:.2f}s")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_letters_all.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_letters_all.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print("ERR:", err)
ssh.close()
