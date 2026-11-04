import paramiko
import sys
import os

print("Connecting to Raspberry Pi 5 (192.168.0.107)...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.107', username='raspberrypi5', timeout=10)

sftp = client.open_sftp()
local_zip = "brailce_update.zip"
remote_zip = "/home/raspberrypi5/brailce_update.zip"

print(f"Uploading {local_zip} ({os.path.getsize(local_zip)/(1024*1024):.1f} MB) to {remote_zip}...")
sftp.put(local_zip, remote_zip)
sftp.close()
print("Upload completed successfully!")

print("Extracting zip on Raspberry Pi 5...")
stdin, stdout, stderr = client.exec_command('unzip -o /home/raspberrypi5/brailce_update.zip -d /home/raspberrypi5/brailce/')
out = stdout.read().decode()
err = stderr.read().decode()
print("Unzip finished.")
if err:
    print("Stderr:", err[:300])

print("Checking files on Raspberry Pi 5:")
stdin, stdout, stderr = client.exec_command('ls -lh /home/raspberrypi5/brailce_update.zip')
print(stdout.read().decode())

client.close()

