import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess
import time

def say(text, scale="1.0"):
    cmd = f"echo '{text}' | /home/raspberrypi5/piper/piper/piper --model /home/raspberrypi5/piper/en_US-ryan-medium.onnx --output-raw --length-scale {scale} | aplay -r 22050 -f S16_LE -t raw -q -"
    subprocess.run(cmd, shell=True)

print("Playing introduction...")
say("Free Input Mode. Ready to type.")
time.sleep(0.5)

say("Here are the keys you liked:")
time.sleep(0.3)
for word in ["Double you", "Jay", "seven", "nine", "minus", "divided by"]:
    say(word)
    time.sleep(0.3)

say("Now listen to the letters A through H:")
time.sleep(0.3)
for letter in ["A.", "B.", "C.", "D.", "E.", "F.", "G.", "H."]:
    say(letter)
    time.sleep(0.3)

print("Audition finished!")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/audition_now.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/audition_now.py')
out = stdout.read().decode('utf-8', errors='replace')
print(out)
ssh.close()
