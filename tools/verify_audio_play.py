import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=5)

remote_script = r'''
import sys
import time
sys.path.insert(0, '/home/raspberrypi5/brailce')

from brailce.config.loader import ConfigLoader
from brailce.speech.service import SpeechService

loader = ConfigLoader()
config = loader.load("/home/raspberrypi5/brailce/brailce/config/config.json")
svc = SpeechService.from_config(config)

print("--- 1. Testing Single Character Keystrokes (Pre-cached Piper Ryan) ---")
print("Playing character 'B'...")
svc.speak_character("B")
time.sleep(1.2)

print("Playing digit '1'...")
svc.speak_character("1")
time.sleep(1.2)

print("Playing operator '+'...")
svc.speak_character("+")
time.sleep(1.2)

print("\n--- 2. Testing Completed Word on Space ---")
print("Playing word 'arm.'...")
svc.speak_text("arm.")
time.sleep(1.8)

print("\n--- 3. Testing AI Mode 'Thinking' ---")
print("Playing 'Thinking, please wait.'...")
svc.speak_text("Thinking, please wait.")
time.sleep(2.5)

print("\n--- 4. Testing Mode Introduction ---")
print("Playing 'Free Input Mode.'...")
svc.speak_text("Free Input Mode.")
time.sleep(2.0)

print("--- Test complete ---")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/verify_audio_play.py', 'w') as f:
    f.write(remote_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/verify_audio_play.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:\n", err)

ssh.exec_command('rm -f /home/raspberrypi5/verify_audio_play.py')
ssh.close()

