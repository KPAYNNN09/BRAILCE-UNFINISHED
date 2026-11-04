import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

items = [
    ("A", []),
    ("A.", []),
    ("B", []),
    ("B.", []),
    ("C", []),
    ("C.", []),
    ("Free Input Mode. Ready to type.", [])
]

for text, extra in items:
    cmd = ["/home/raspberrypi5/piper/piper/piper", "--model", "/home/raspberrypi5/piper/en_US-ryan-medium.onnx", "--output-raw"] + extra
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate(input=(text + "\\n").encode())
    dur = len(out) / (22050 * 2)
    print(f"Text: '{text}' -> dur: {dur:.3f}s")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_voice_match.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_voice_match.py')
print(stdout.read().decode('utf-8', errors='replace'))
ssh.close()
