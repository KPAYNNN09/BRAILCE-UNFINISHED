import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

test_code = """
import keyboard
try:
    keyboard.hook(lambda e: None)
    print('SUCCESS WITH SUDO: Raw hardware keyboard hook active!')
    keyboard.unhook_all()
except Exception as e:
    print('Error even with sudo:', e)
"""

stdin, stdout, stderr = ssh.exec_command(f"echo raspberrypi5 | sudo -S /home/raspberrypi5/brailce/venv/bin/python3 -c \"{test_code}\"")
print(stdout.read().decode('utf-8', errors='replace').strip())
err = stderr.read().decode('utf-8', errors='replace').strip()
if err:
    print("ERR:", err)

ssh.close()
