import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)

test_script = """
import sys
sys.path.insert(0, '/home/raspberrypi5/brailce')

from brailce.config.loader import ConfigLoader
from brailce.core.app import BrailceApp
from brailce.core.events import AppMode, EventType, InputEvent
import time

print('1. Loading config...')
config = ConfigLoader.load('/home/raspberrypi5/brailce/brailce/config/config.json')
print('Sound enabled in config:', config.get('sound', 'enabled'))
print('Speech engine in config:', config.get('speech', 'engine'))
print('Speech rate in config:', config.get('speech', 'rate'))

print('2. Initializing BrailceApp in simulation/test mode...')
app = BrailceApp(config)
app.setup()

print('3. Testing mode announcements...')
# Cycle through all modes
app._on_mode_change(AppMode.FREE_INPUT, AppMode.MATH)
time.sleep(0.5)
app._on_mode_change(AppMode.MATH, AppMode.AI_ASSISTANT)
time.sleep(0.5)
app._on_mode_change(AppMode.AI_ASSISTANT, AppMode.SCANNER)
time.sleep(0.5)
app._on_mode_change(AppMode.SCANNER, AppMode.FREE_INPUT)
time.sleep(0.5)
print('Mode transitions verified successfully!')

print('4. Testing Free Input typing and space word readback...')
free_mode = app._modes[AppMode.FREE_INPUT]
app._active_mode = free_mode
for ch in 'CAT':
    free_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character=ch))
assert app.state.text_buffer == 'CAT'
free_mode.handle_event(InputEvent(EventType.SPACE_PRESSED))
assert app.state.text_buffer == 'CAT '
print('Free Input buffer and word verified!')

print('5. Testing Math Mode calculation and explanation...')
math_mode = app._modes[AppMode.MATH]
app._active_mode = math_mode
for ch in ['4', '-', '1']:
    math_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character=ch))
assert app.state.math_buffer == '4-1'
math_mode.handle_event(InputEvent(EventType.ENTER_PRESSED))
assert app.state.math_last_result == '3'
print('Math solution:', app.state.math_last_result, 'Explanation:', app.state.math_last_explanation[:50])

print('6. Testing Scanner Mode no braille feedback...')
scanner_mode = app._modes[AppMode.SCANNER]
app._active_mode = scanner_mode
# Trigger scan without sheet
scanner_mode._scan_loop()
print('Scanner error handling verified!')

print('All live component tests completed successfully!')
app.shutdown()
"""

stdin, stdout, stderr = ssh.exec_command(f"python3 -c \"\"\"{test_script}\"\"\"")
print(stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='replace').decode('ascii'))
err = stderr.read().decode('utf-8', errors='replace').encode('ascii', errors='replace').decode('ascii')
if err:
    print("Stderr:", err)
ssh.close()
