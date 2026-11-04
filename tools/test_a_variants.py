import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

phrases = [
    'the letter A',
    'the letter a',
    'the letter eh',
    'the letter eigh',
    'letter A',
    'the letter ay',
]

for p in phrases:
    p2 = subprocess.Popen(['espeak-ng', '-v', 'en-us', '-q', '--ipa', p], stdout=subprocess.PIPE)
    ipa = p2.communicate()[0].decode().strip()
    
    cmd = ['/home/raspberrypi5/piper/piper/piper', '--model', '/home/raspberrypi5/piper/en_US-ryan-medium.onnx', '--output-raw']
    p_pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw, _ = p_pipe.communicate(input=(p + '\\n').encode())
    dur = len(raw) / (22050 * 2)
    print(f"{p:20} -> ipa: {ipa:30} dur: {dur:.2f}s")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_a_var.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_a_var.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print("ERR:", err)
ssh.close()
