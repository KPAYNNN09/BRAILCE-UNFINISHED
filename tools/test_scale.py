import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

candidates_A = [
    ("A.", 1.0),
    ("A.", 1.5),
    ("A.", 2.0),
    ("A.", 2.5),
    ("Ay.", 1.5),
    ("aye.", 1.5),
    ("eigh.", 1.5),
]

for text, scale in candidates_A:
    cmd = ["/home/raspberrypi5/piper/piper/piper", "--model", "/home/raspberrypi5/piper/en_US-ryan-medium.onnx", "--output-raw", "--length-scale", str(scale)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate(input=(text + "\\n").encode())
    dur = len(out) / (22050 * 2)
    print(f"Text: '{text:10s}' scale={scale:4.1f} -> dur={dur:.3f}s")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_durations.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_durations.py')
out = stdout.read().decode('utf-8', errors='replace')
print(out)
ssh.close()
