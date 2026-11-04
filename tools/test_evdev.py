import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

test_code = """
try:
    import evdev
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    print('evdev devices found:', [d.name for d in devices])
except Exception as e:
    print('evdev test:', e)
"""

stdin, stdout, stderr = ssh.exec_command(f"/home/raspberrypi5/brailce/venv/bin/python3 -c \"{test_code}\"")
print(stdout.read().decode('utf-8', errors='replace').strip())
err = stderr.read().decode('utf-8', errors='replace').strip()
if err:
    print("ERR:", err)

ssh.close()
