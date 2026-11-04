import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

candidates = [
    # A
    "A", "ay", "eigh", "ae", "ey", "Hay"[1:],
    # B
    "Bee", "be",
    # C
    "See", "sea",
    # D
    "Dee",
    # E
    "Ee", "Eee",
    # F
    "Eff", "ef",
    # G
    "Jee", "gee",
    # H
    "Aitch", "H",
    # I
    "Eye", "Aye",
    # J
    "Jay",
    # K
    "Kay",
    # L
    "Ell",
    # M
    "Emm",
    # N
    "Enn",
    # O
    "Oh",
    # P
    "Pee", "pea",
    # Q
    "Cue", "queue",
    # R
    "Are", "ar",
    # S
    "Ess",
    # T
    "Tee", "tea",
    # U
    "You",
    # V
    "Vee",
    # W
    "double you",
    # X
    "Ex",
    # Y
    "Why",
    # Z
    "Zee"
]

for w in candidates:
    cmd = ["espeak-ng", "-v", "en-us", "-q", "--ipa", w]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ipa = p.communicate()[0].decode().strip()
    print(f"{w:12s} -> {repr(ipa)}")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_spellings.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_spellings.py')
print(stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii'))
ssh.close()
