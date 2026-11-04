import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = r'''
import subprocess
import time

def play(text, scale="1.0"):
    cmd = ["echo", text]
    p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    piper = subprocess.Popen(
        ["/home/raspberrypi5/piper/piper/piper", "--model", "/home/raspberrypi5/piper/en_US-ryan-medium.onnx", "--output-raw", "--length-scale", scale],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    p1.stdout.close()
    aplay = subprocess.Popen(
        ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-q", "-"],
        stdin=piper.stdout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    piper.stdout.close()
    aplay.wait()
    piper.wait()

def inspect(label, text):
    cmd_esp = ["espeak-ng", "-v", "en-us", "-q", "--ipa", text]
    p = subprocess.Popen(cmd_esp, stdout=subprocess.PIPE)
    ipa = p.communicate()[0].decode().strip()
    print(f"{label:12} | text: {text:15} | ipa: {ipa}")
    play(text)
    time.sleep(0.3)

print("=== 1. Testing A (bare, not the letter) ===")
inspect("A bare", "A")
inspect("A dot", "A.")
inspect("eigh", "eigh")

print("=== 2. Testing M, N, S intonation ===")
inspect("M letter", "M.")
inspect("M em", "Em.")
inspect("N letter", "N.")
inspect("N en", "En.")
inspect("S letter", "S.")
inspect("S ess", "Ess.")

print("=== 3. Testing plus (bare, not plus sign) ===")
inspect("plus", "plus")
inspect("plus dot", "plus.")

print("=== 4. Testing divided by vs multiplied by ===")
inspect("div by", "divided by")
inspect("div by dot", "divided by.")
inspect("mult by", "multiplied by")
inspect("mult by dot", "multiplied by.")

print("=== 5. Testing punctuation (. and ,) ===")
inspect("period", "period")
inspect("period dot", "period.")
inspect("dot", "dot")
inspect("comma", "comma")
inspect("comma dot", "comma.")

print("=== 6. Testing word pronunciation ===")
inspect("cat lower", "cat")
inspect("cat dot", "cat.")
inspect("CAT upper", "CAT")
inspect("dog lower", "dog")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_exact_spec.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_exact_spec.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print("ERR:", err)
ssh.close()
