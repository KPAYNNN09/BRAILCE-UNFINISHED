import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=5)

remote_test = r'''
import subprocess
import wave
import io
import os

PIPER_BIN = "/home/raspberrypi5/piper/piper/piper"
PIPER_MODEL = "/home/raspberrypi5/piper/en_US-ryan-medium.onnx"

utterances = [
    ("Mode Intro", "Free Input Mode."),
    ("AI Full Response", "Hello! I am your Brailce AI tutor."),
    ("Thinking short", "thinking."),
    ("Thinking phrase", "Thinking, please wait."),
    ("Word cat", "cat."),
    ("Word arm", "arm."),
    ("Letter A", "A."),
    ("Letter B", "B."),
    ("Letter C", "C."),
    ("Letter H", "H."),
    ("Digit 1", "one."),
    ("Operator plus", "plus."),
]

print("=== PIPER SYNTHESIS TEST ===")
for label, text in utterances:
    cmd = [
        PIPER_BIN,
        "--model", PIPER_MODEL,
        "--output-raw",
        "--length-scale", "1.0",
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw_pcm, err = p.communicate(text.encode("utf-8") + b"\n")
    duration = len(raw_pcm) / (22050 * 2)
    print(f"{label:20} text={text!r:25} raw_pcm_bytes={len(raw_pcm):7} duration={duration:.3f}s")
'''

stdin, stdout, stderr = ssh.exec_command('python3 -c "' + remote_test.replace('"', '\\"') + '"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:\n", err)
ssh.close()

