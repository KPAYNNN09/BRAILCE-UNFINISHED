import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

for word in ["A", "eigh", "Ay", "ey", "Eh"]:
    cmd = ["/home/raspberrypi5/piper/piper/piper", "--model", "/home/raspberrypi5/piper/en_US-ryan-medium.onnx", "--output-raw"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate(input=(word + "\\n").encode())
    dur = len(out) / (22050 * 2)
    # Check what phonemes were fed to piper by checking espeak
    cmd2 = ["espeak-ng", "-v", "en-us", "-q", "--ipa", word]
    p2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE)
    ipa = p2.communicate()[0].decode().strip()
    print(f"'{word}': ipa={ipa} dur={dur:.3f}s")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_a.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_a.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
ssh.close()
