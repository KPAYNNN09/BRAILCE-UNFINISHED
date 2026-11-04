import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = '''
import subprocess

words_to_check = [
    # A candidates
    ("A", "eigh"),
    ("A", "ay"),
    ("A", "Eh"),
    ("A", "A"),
    # B
    ("B", "bee"),
    # C
    ("C", "sea"),
    # D
    ("D", "dee"),
    # E
    ("E", "ee"),
    # F
    ("F", "ef"),
    # G
    ("G", "gee"),
    # H
    ("H", "aitch"),
    # J
    ("J", "Jay"),
    # K
    ("K", "kay"),
    # L
    ("L", "el"),
    # M
    ("M", "em"),
    # N
    ("N", "en"),
    # O
    ("O", "oh"),
    # P
    ("P", "pea"),
    # Q
    ("Q", "cue"),
    # R
    ("R", "are"),
    # S
    ("S", "ess"),
    # T
    ("T", "tea"),
    # U
    ("U", "you"),
    # V
    ("V", "vee"),
    # W
    ("W", "Double you"),
    # X
    ("X", "ex"),
    # Y
    ("Y", "why"),
    # Z
    ("Z", "zee"),
]

for letter, word in words_to_check:
    p = subprocess.Popen(["espeak-ng", "-v", "en-us", "-q", "--ipa", word], stdout=subprocess.PIPE)
    ipa = p.communicate()[0].decode().strip()
    
    cmd = ["/home/raspberrypi5/piper/piper/piper", "--model", "/home/raspberrypi5/piper/en_US-ryan-medium.onnx", "--output-raw"]
    p2 = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, _ = p2.communicate(input=(word + "\\n").encode())
    dur = len(out) / (22050 * 2)
    print(f"{letter} ({word:12s}) -> ipa={repr(ipa):20s} dur={dur:.3f}s")
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_word_list.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /home/raspberrypi5/test_word_list.py')
out = stdout.read().decode('utf-8', errors='replace')
print(out.encode('ascii', errors='backslashreplace').decode('ascii'))
ssh.close()
