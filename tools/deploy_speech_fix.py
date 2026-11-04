"""Check Brailce status on Pi, kill if stuck, restart cleanly."""
import paramiko

PI_HOST = "192.168.0.107"
PI_USER = "raspberrypi5"

print("Connecting to Pi...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(PI_HOST, username=PI_USER, timeout=10)
print("Connected!")

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode(errors='replace').strip(), stderr.read().decode(errors='replace').strip()

# Check if brailce is running
print("\n[1] Checking if Brailce is running...")
out, _ = run("ps aux | grep -i brailce | grep -v grep")
if out:
    print(f"  Running processes:\n{out}")
else:
    print("  NOT running!")

# Check for stuck piper processes
print("\n[2] Checking for stuck piper processes...")
out, _ = run("ps aux | grep -i piper | grep -v grep")
if out:
    print(f"  Piper processes:\n{out}")
else:
    print("  No piper processes.")

# Check last log output
print("\n[3] Last 20 lines of brailce log...")
out, _ = run("tail -20 /tmp/brailce.log 2>/dev/null")
if out:
    for line in out.split('\n'):
        try:
            print(f"  {line}")
        except:
            print("  [encoding error]")
else:
    print("  No log file found.")

# Kill everything and restart fresh
print("\n[4] Killing ALL brailce and piper processes...")
run("pkill -9 -f 'python3.*brailce' 2>/dev/null")
run("pkill -9 -f piper 2>/dev/null")
run("pkill -9 -f aplay 2>/dev/null")
import time
time.sleep(1)
print("  Done.")

# Clear pycache again just in case
print("\n[5] Clearing __pycache__...")
run("find /home/raspberrypi5/brailce -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null")
print("  Done.")

# Restart
print("\n[6] Starting Brailce fresh...")
run("cd ~/brailce && nohup ./venv/bin/python3 -m brailce > /tmp/brailce.log 2>&1 &")
time.sleep(3)

# Verify it started
out, _ = run("ps aux | grep -i brailce | grep -v grep")
if out:
    print(f"  Brailce is running!")
else:
    print("  WARNING: Brailce did not start! Check logs.")
    out, _ = run("tail -30 /tmp/brailce.log 2>/dev/null")
    for line in out.split('\n'):
        try:
            print(f"  {line}")
        except:
            print("  [encoding error]")

ssh.close()
print("\n=== DONE ===")
print("\nTo switch modes: Press TAB or F1 (not ESC)")
print("ESC = quit the app entirely")
