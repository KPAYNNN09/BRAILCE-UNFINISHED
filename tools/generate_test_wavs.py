import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=5)

remote_test = r'''
import subprocess
import wave
import os

PIPER_BIN = "/home/raspberrypi5/piper/piper/piper"
PIPER_MODEL = "/home/raspberrypi5/piper/en_US-ryan-medium.onnx"
OUT_DIR = "/home/raspberrypi5/test_wavs"
os.makedirs(OUT_DIR, exist_ok=True)

test_phrases = [
    ("thinking_wait", "Thinking, please wait.", 1.0),
    ("thinking_dot", "Thinking...", 1.0),
    ("word_apple", "apple.", 1.0),
    ("word_arm", "arm.", 1.0),
    ("char_A", "A.", 1.05),
    ("char_B", "B.", 1.05),
    ("char_C", "C.", 1.05),
    ("char_H", "H.", 1.05),
    ("digit_1", "one.", 1.05),
    ("math_plus", "plus.", 1.05),
    ("mode_free_input", "Free Input Mode.", 1.0),
]

for name, text, scale in test_phrases:
    tmp = f"/tmp/{name}_raw.wav"
    out = f"{OUT_DIR}/{name}.wav"
    cmd = [
        PIPER_BIN,
        "--model", PIPER_MODEL,
        "--output_file", tmp,
        "--length-scale", str(scale),
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p.communicate(text.encode("utf-8") + b"\n")
    
    with wave.open(tmp, "rb") as wf:
        params = wf.getparams()
        frames = wf.readframes(wf.getnframes())
    os.remove(tmp)
    
    pre_bytes = b"\x00" * int(params.framerate * 0.15 * params.nchannels * params.sampwidth)
    post_bytes = b"\x00" * int(params.framerate * 0.20 * params.nchannels * params.sampwidth)
    
    with wave.open(out, "wb") as wf:
        wf.setparams(params)
        wf.writeframes(pre_bytes + frames + post_bytes)
        
    print(f"Generated {out}: frames={wf.getnframes()}, rate={wf.getframerate()}, dur={wf.getnframes()/wf.getframerate():.3f}s")
'''

stdin, stdout, stderr = ssh.exec_command('python3 -c "' + remote_test.replace('"', '\\"') + '"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:\n", err)

ssh.close()

