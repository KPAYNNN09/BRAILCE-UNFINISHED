import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=5)

remote_test = r'''
import sys
import wave
import os

sys.path.insert(0, '/home/raspberrypi5/brailce')

from brailce.speech.normalizer import (
    is_keystroke_feedback,
    normalize_for_piper,
    normalize_for_espeak_character,
    KEYSTROKE_SOUND_NAMES,
)
from brailce.speech.piper_engine import PiperEngine, _find_cache_dir

print("=== NORMALIZER TESTS ===")
for test in ["A", "B", "B.", "1", "1.", "+", "plus", "plus.", "arm", "arm.", "Thinking", "Thinking, please wait."]:
    print(f"text={test!r}: is_keystroke={is_keystroke_feedback(test)}, norm_espeak={normalize_for_espeak_character(test)!r}, norm_piper={normalize_for_piper(test)!r}")

print("\n=== CACHE DIR & FILES ===")
cdir = _find_cache_dir()
print(f"Cache dir: {cdir}")
if cdir and os.path.isdir(cdir):
    for f in ["char_A.wav", "char_B.wav", "char_1.wav", "char_plus.wav"]:
        p = os.path.join(cdir, f)
        if os.path.isfile(p):
            with wave.open(p, 'rb') as wf:
                print(f"{f}: channels={wf.getnchannels()}, width={wf.getsampwidth()}, rate={wf.getframerate()}, frames={wf.getnframes()}, duration={wf.getnframes()/wf.getframerate():.3f}s")
        else:
            print(f"{f}: NOT FOUND")

print("\n=== ENGINE CHECK ===")
pe = PiperEngine()
print(f"Piper available: {pe.is_available()}")
print(f"Piper binary: {pe._binary}")
print(f"Piper model: {pe._model}")

'''

stdin, stdout, stderr = ssh.exec_command('python3 -c "' + remote_test.replace('"', '\\"') + '"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:\n", err)
ssh.close()

