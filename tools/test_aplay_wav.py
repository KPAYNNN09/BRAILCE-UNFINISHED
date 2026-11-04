import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=5)

remote_test = r'''
import subprocess

wav_file = "/home/raspberrypi5/test_wavs/word_apple.wav"

print("1. Testing aplay with WAV file directly:")
res = subprocess.run(["aplay", "-v", wav_file], capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)

print("\n2. Testing aplay via stdin with WAV header:")
with open(wav_file, "rb") as f:
    wav_bytes = f.read()

res2 = subprocess.run(["aplay", "-v", "-"], input=wav_bytes, capture_output=True)
print("STDOUT:", res2.stdout.decode(errors='replace'))
print("STDERR:", res2.stderr.decode(errors='replace'))
'''

stdin, stdout, stderr = ssh.exec_command('python3 -c "' + remote_test.replace('"', '\\"') + '"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:\n", err)
ssh.close()

