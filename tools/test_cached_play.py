import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=5)

remote_test = r'''
import sys
import os

sys.path.insert(0, '/home/raspberrypi5/brailce')

from brailce.speech.piper_engine import PiperEngine

pe = PiperEngine()
print("Testing play_cached_character for 'B.':")
res_B = pe.play_cached_character("B.")
print("Result for 'B.':", res_B)

print("Testing play_cached_character for '1.':")
res_1 = pe.play_cached_character("1.")
print("Result for '1.':", res_1)

print("Testing play_cached_character for 'plus.':")
res_plus = pe.play_cached_character("plus.")
print("Result for 'plus.':", res_plus)
'''

stdin, stdout, stderr = ssh.exec_command('python3 -c "' + remote_test.replace('"', '\\"') + '"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:\n", err)
ssh.close()

