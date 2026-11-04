import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

for text in ["A.", "Ay.", "B.", "Bee.", "C.", "See.", "H.", "Aitch.", "R.", "Arr.", "Z.", "Zee."]:
    cmd = ["espeak-ng", "-v", "en-us", "-q", "--ipa", text]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    print(f"{text:8s} -> {out.decode().strip()}")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_ipa.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_ipa.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
err = stderr.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
if err:
    print("ERR:", err)
ssh.close()
