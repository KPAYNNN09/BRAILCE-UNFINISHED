import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

print("Killing all Brailce, Piper, and aplay processes on Pi...")
ssh.exec_command("pkill -9 -f 'python3.*brailce' ; pkill -9 -f piper ; pkill -9 -f aplay")
time.sleep(1)

stdin, stdout, stderr = ssh.exec_command("ps aux | grep -i brailce | grep -v grep")
out = stdout.read().decode('utf-8', errors='replace').strip()
if out:
    print("Warning, still running:\n", out)
else:
    print("ALL Brailce processes stopped! The Pi is free and ready for PuTTY.")

ssh.close()
