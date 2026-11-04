import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    p1 = subprocess.Popen(["espeak-ng", "-v", "en-us", "-q", "--ipa", ch], stdout=subprocess.PIPE)
    ipa1 = p1.communicate()[0].decode().strip()
    
    p2 = subprocess.Popen(["espeak-ng", "-v", "en-us", "-q", "--ipa", f"{ch}."], stdout=subprocess.PIPE)
    ipa2 = p2.communicate()[0].decode().strip()
    
    print(f"{ch}: bare={repr(ipa1):15s} dot={repr(ipa2)}")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_ipa_all.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_ipa_all.py')
out = stdout.read().decode('utf-8', errors='replace')
print(out.encode('ascii', errors='backslashreplace').decode('ascii'))
ssh.close()
