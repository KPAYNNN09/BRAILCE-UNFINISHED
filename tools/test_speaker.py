import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

# Test speech with Piper on the speaker
cmd = "echo 'Testing speech on Raspberry Pi 5. Free Input Mode.' | /home/raspberrypi5/piper/piper/piper --model /home/raspberrypi5/piper/en_US-ryan-medium.onnx --output-raw | aplay -r 22050 -f S16_LE -t raw -q -"
subprocess.run(cmd, shell=True)
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_speaker.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_speaker.py')
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print("OUT:", out)
if err:
    print("ERR:", err)
ssh.close()
