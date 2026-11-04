import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=5)

remote_test = r'''
import subprocess

cmds = [
    ("APLAY -l", "aplay -l"),
    ("ASOUND CONF", "cat /etc/asound.conf 2>/dev/null || cat ~/.asoundrc 2>/dev/null || echo 'No asound conf'"),
    ("MIXER", "amixer scontrols 2>/dev/null || echo 'No mixer controls'"),
    ("CURRENT APLAY ARGS", "which aplay")
]

for label, cmd in cmds:
    print(f"=== {label} ===")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("ERR:", res.stderr)
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_alsa.py', 'w') as f:
    f.write(remote_test)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_alsa.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:\n", err)
ssh.close()

