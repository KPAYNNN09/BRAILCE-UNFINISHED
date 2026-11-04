import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=5)

remote_test = r'''
import sys
sys.path.insert(0, '/home/raspberrypi5/brailce')

from brailce.config.loader import ConfigLoader
from brailce.speech.service import SpeechService

loader = ConfigLoader()
config = loader.load("/home/raspberrypi5/brailce/brailce/config/config.json")
svc = SpeechService.from_config(config)

print("Character Engine:", svc._character_engine.engine_name)
print("Text Engine:", svc._text_engine.engine_name)
print("Speech Behavior:", svc._behavior)
'''

stdin, stdout, stderr = ssh.exec_command('python3 -c "' + remote_test.replace('"', '\\"') + '"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:\n", err)
ssh.close()
