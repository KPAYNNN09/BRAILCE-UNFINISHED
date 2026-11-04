import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

test_code = """
import keyboard
print('Testing keyboard hook on Pi...')
try:
    keyboard.hook(lambda e: print(e))
    print('Keyboard hook SUCCESSFUL!')
    keyboard.unhook_all()
except Exception as e:
    print('Keyboard hook error:', e)
"""

stdin, stdout, stderr = ssh.exec_command(f"/home/raspberrypi5/brailce/venv/bin/python3 -c \"{test_code}\"")
print(stdout.read().decode('utf-8', errors='replace').strip())
err = stderr.read().decode('utf-8', errors='replace').strip()
if err:
    print("ERR:", err)

ssh.close()
