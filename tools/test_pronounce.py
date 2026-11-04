import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

# Let us test how Piper Ryan pronounces various phrases for the letters
candidates = [
    ("A", "letter A"),
    ("A", "capital A"),
    ("A", "A"),
    ("A", "Eh"),
    ("B", "Bee"),
    ("B", "letter B"),
    ("B", "B."),
    ("C", "See"),
    ("C", "letter C"),
    ("D", "Dee"),
    ("E", "Ee"),
    ("F", "Eff"),
    ("G", "Jee"),
    ("H", "Aitch"),
    ("H", "letter H"),
    ("I", "Eye"),
    ("K", "Kay"),
    ("L", "Ell"),
    ("M", "Emm"),
    ("N", "Enn"),
    ("O", "Oh"),
    ("P", "Pee"),
    ("Q", "Cue"),
    ("R", "Are"),
    ("S", "Ess"),
    ("T", "Tee"),
    ("U", "You"),
    ("V", "Vee"),
    ("X", "Ex"),
    ("Y", "Why"),
    ("Z", "Zee")
]

for orig, word in candidates:
    cmd = ["/home/raspberrypi5/piper/piper/piper", "--model", "/home/raspberrypi5/piper/en_US-ryan-medium.onnx", "--output-raw"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate(input=(word + "\\n").encode())
    dur = len(out) / (22050 * 2)
    print(f"{orig} -> '{word}': {dur:.3f}s")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_pronounce.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_pronounce.py')
print(stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii'))
ssh.close()
