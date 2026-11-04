import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

for w in ["cat", "CAT", "kat", "c-a-t", "c a t", "kæt"]:
    cmd_esp = ["espeak-ng", "-v", "en-us", "-q", "--ipa", w]
    p = subprocess.Popen(cmd_esp, stdout=subprocess.PIPE)
    ipa = p.communicate()[0].decode().strip()

    cmd = ["/home/raspberrypi5/piper/piper/piper", "--model", "/home/raspberrypi5/piper/en_US-ryan-medium.onnx", "--output-raw"]
    p_pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw, _ = p_pipe.communicate(input=(w + "\\n").encode())
    dur = len(raw) / (22050 * 2)
    print(f"{w:10} | ipa: {ipa:20} | dur: {dur:.2f}s")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_cat.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_cat.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
ssh.close()
