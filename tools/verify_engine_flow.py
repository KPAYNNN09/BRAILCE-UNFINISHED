import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

script = r'''
import os
import sys
import numpy as np

sys.path.insert(0, '/home/raspberrypi5/brailce')

from brailce.vision.obr_engine import OBREngine
from brailce.speech.service import SpeechService
from brailce.speech.piper_engine import PiperEngine

print('=== 1. Testing Empty Camera / Dark Frame OBR Gate (3 Scans) ===')
obr = OBREngine()

# Scan 1: All black frame (camera covered / sensor in darkness)
dark_frame = np.zeros((480, 640, 3), dtype=np.uint8)
# Scan 2: Dim noisy frame (ambient sensor noise without paper)
noisy_dim_frame = np.random.randint(20, 60, (480, 640, 3), dtype=np.uint8)
# Scan 3: Uniform flat gray frame (no embossed dot contrast)
flat_gray_frame = np.full((480, 640, 3), 120, dtype=np.uint8)

for i, frame in enumerate([dark_frame, noisy_dim_frame, flat_gray_frame], 1):
    has_paper = obr.has_paper_background(frame)
    presence = obr.detect_braille_presence(frame)
    proc_res = obr.process_image(frame)
    print(f'Scan {i}: has_paper={has_paper}, presence={presence}, readable={proc_res["readable"]}, text={proc_res["text"]!r}')
    assert presence is False, f'Scan {i} failed: presence was True on empty frame!'
    assert proc_res['readable'] is False, f'Scan {i} failed: readable was True on empty frame!'

print('>>> ALL 3 EMPTY SCANS RETURNED: False / No Braille detected! PASS!')

print('\n=== 2. Testing Problematic Character WAV Files on Pi ===')
cache_dir = '/home/raspberrypi5/brailce/brailce/audio/characters'
test_chars = [
    ('S', 'char_S.wav'),
    ('H', 'char_H.wav'),
    ('X', 'char_X.wav'),
    ('6', 'char_6.wav'),
    ('+', 'char_plus.wav'),
    ('-', 'char_minus.wav'),
    ('*', 'char_times.wav'),
    ('/', 'char_divide.wav'),
    ('?', 'char_question.wav'),
    ('!', 'char_exclamation.wav'),
]

piper = PiperEngine()
for char, fname in test_chars:
    fpath = os.path.join(cache_dir, fname)
    assert os.path.isfile(fpath), f'Missing WAV file {fpath}'
    size = os.path.getsize(fpath)
    assert size > 5000, f'WAV file {fpath} too small ({size} bytes)'
    # Test cached playback function
    can_play = piper.play_cached_character(char)
    print(f'OK: {char} -> {fname} ({size} bytes, playable={can_play})')

print('>>> ALL 10 TARGET CHARACTER WAVS VERIFIED ON PI!')

print('\n=== 3. Testing Single-Letter Routing in SpeechService ===')
from unittest.mock import MagicMock
service = SpeechService(character_engine=piper, text_engine=piper)
service.speak_character = MagicMock()

# Typing single letter 'S' and pressing Space or Enter routes to speak_character:
service.speak_word('S')
service.speak_character.assert_called_with('S')

service.speak_text('S')
service.speak_character.assert_called_with('S')

service.speak('S')
service.speak_character.assert_called_with('S')

service.speak_word('s')
service.speak_character.assert_called_with('s')

print('>>> SpeechService single-letter SPACE/ENTER routing PASSED!')

print('\n=== 4. Testing Live Word and Character Synthesis Pipeline on Pi ===')
real_service = SpeechService()
# Test speaking a single word (e.g. on SPACE) - must directly synthesize without slicing
print('Testing direct single-word speak_word("apple")...')
real_service.speak_word('apple')
import time
time.sleep(1.5)

print('Testing character cached playback speak_character("A")...')
real_service.speak_character('A')
time.sleep(1.0)

print('Testing single-letter word on space speak_word("S")...')
real_service.speak_word('S')
time.sleep(1.0)

print('>>> ALL LIVE AUDIO TESTS EXECUTED CLEANLY WITHOUT ERRORS!')
'''

sftp = ssh.open_sftp()
with sftp.file('/home/raspberrypi5/test_flow.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('/home/raspberrypi5/brailce/venv/bin/python3 /home/raspberrypi5/test_flow.py')
out = stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='backslashreplace').decode('ascii')
print(out)
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print("ERR:", err)

# Ensure everything is killed so user has clean terminal
ssh.exec_command("pkill -9 -f piper 2>/dev/null; pkill -9 -f aplay 2>/dev/null; pkill -9 -f 'python3.*brailce' 2>/dev/null")

ssh.close()
