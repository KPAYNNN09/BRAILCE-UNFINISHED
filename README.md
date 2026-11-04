# Brailce – A Portable Braille-to-Voice Assistive Device

**Thesis Prototype**

Brailce is a portable Raspberry Pi 5-based assistive device that allows users to press dedicated physical character buttons labeled with embossed Braille, receive immediate spoken feedback, build text through repeated key presses, and interact with a locally hosted offline AI assistant using Ollama.

---

## Key Architectural Concept

### Dedicated Braille Character Keypad

The physical input system uses a **dedicated character keypad** — NOT a traditional six-button Braille-dot keyboard.

Each supported character has its own physical button. The keycap contains the corresponding **embossed Braille representation** of that character.

**Example:**

```
Physical Button: [A]
Keycap: A with embossed Braille pattern ⠁
Software meaning: "A"
```

When the [A] button is pressed:
1. The system identifies the character "A"
2. Looks up the corresponding Braille pattern (Dot 1 → ⠁)
3. Appends "A" to the text buffer
4. Displays the character and its Braille representation
5. Speaks the configured character name immediately through Piper TTS
6. Logs the event

**The laptop keyboard simulates the dedicated character buttons during software development.**

---

## Application Modes

### 1. Free Input Mode (Default)

Each character button press immediately produces audible feedback.

```
Press [A] → speak "A" → buffer: "A"
Press [B] → speak "B" → buffer: "AB"
Press [C] → speak "C" → buffer: "ABC"
```

### 2. AI Assistant Mode

Natural language input is sent to a locally hosted Ollama LLM for offline AI responses.

```
Type: "What is Braille?" → Press Enter → AI processes → speaks response
```

Switch between modes using the **F1** key (laptop) or the dedicated **MODE** button (hardware).

---

## Laptop Simulation

During development, the laptop keyboard simulates the dedicated character buttons:

| Laptop Key | Simulates |
|-----------|-----------|
| A–Z | Dedicated letter buttons |
| 0–9 | Dedicated number buttons |
| + - * / | Dedicated math operator buttons |
| Space | SPACE button |
| Backspace | BACKSPACE button |
| F1 | MODE button |
| F2 | CLEAR button |
| F11 | VOLUME DOWN button |
| F12 | VOLUME UP button |
| Esc | QUIT |
| Enter | ENTER / AI Submit |

**This is a one-key-per-character simulation, NOT a six-dot Braille combination input.**

---

## System Dependencies

### Required (System-Level)

| Dependency | Purpose | Install |
|-----------|---------|---------|
| **Python 3.11+** | Runtime | [python.org](https://python.org) |
| **Piper TTS** | Offline neural text-to-speech | [Piper](https://github.com/rhasspy/piper) |
| **Ollama** | Local LLM inference | [ollama.ai](https://ollama.ai) |

### Python Dependencies

```bash
pip install -r requirements.txt
```

### Hardware-Only (NOT required for laptop)

- `gpiozero` — Raspberry Pi GPIO control
- `spidev` — SPI interface for TFT display
- `Pillow` — Image rendering for TFT

---

## Quick Start

```bash
# 1. Clone/download the project

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Piper's Python package and voice model
pip install piper-tts
# Place en_US-ryan-medium.onnx and en_US-ryan-medium.onnx.json
# in ~/piper, or update speech.model_path in brailce/config/config.json.

# 4. Run the application
python main.py

# 5. Run with debug logging
python main.py --debug

# 6. Run with custom config
python main.py --config path/to/config.json
```

---

## Configuration

Edit `brailce/config/config.json`:

```json
{
    "system": {
        "simulation_mode": true
    },
    "input": {
        "device": "keyboard"
    },
    "speech": {
        "enabled": true,
        "engine": "piper",
        "model_path": "~/piper/en_US-ryan-medium.onnx",
        "length_scale": 1.08,
        "noise_scale": 0.5,
        "noise_w": 0.6,
        "sentence_silence": 0.2,
        "volume": 100,
        "digit_token_mode": "number",
        "speak_each_character": true
    },
    "ai": {
        "enabled": true,
        "host": "http://127.0.0.1:11434",
        "model": "MODEL_NAME_HERE"
    }
}
```

---

## Project Structure

```
brailce/
├── main.py                      # Entry point
├── requirements.txt             # Python dependencies
├── README.md                    # This file
│
├── brailce/
│   ├── config/                  # Configuration loading
│   │   ├── config.json          # User configuration
│   │   ├── defaults.py          # Default values
│   │   └── loader.py            # JSON loader with deep merge
│   │
│   ├── core/                    # Application core
│   │   ├── app.py               # Main application controller
│   │   ├── events.py            # Event types and data models
│   │   ├── mode_manager.py      # Mode switching logic
│   │   └── state.py             # Mutable application state
│   │
│   ├── input/                   # Input device abstraction
│   │   ├── base.py              # Abstract input device
│   │   ├── keyboard_input.py    # Laptop keyboard simulation
│   │   └── gpio_keypad.py       # Future GPIO keypad (stub)
│   │
│   ├── braille/                 # Braille mapping and encoding
│   │   ├── models.py            # BrailleMapping dataclass
│   │   ├── mapping.py           # Mapping service
│   │   ├── encoder.py           # Character-to-Braille encoder
│   │   ├── arithmetic.py        # Safe arithmetic (stub)
│   │   └── mappings/            # JSON mapping tables
│   │       ├── letters.json
│   │       ├── numbers.json
│   │       ├── punctuation.json
│   │       ├── math.json
│   │       └── nemeth.json
│   │
│   ├── modes/                   # Application modes
│   │   ├── base_mode.py         # Abstract mode
│   │   ├── free_input.py        # Free Input Mode
│   │   └── ai_assistant.py      # AI Assistant Mode
│   │
│   ├── speech/                  # Text-to-speech
│   │   ├── base.py              # Abstract speech engine
│   │   ├── piper_engine.py      # Shared Piper synthesis and playback
│   │   └── pronunciation.py     # Character pronunciation table
│   │
│   ├── display/                 # Display output
│   │   ├── base.py              # Abstract display
│   │   ├── console_display.py   # Terminal output (laptop)
│   │   └── ili9488_display.py   # TFT display (stub)
│   │
│   ├── ai/                      # AI assistant (stub)
│   ├── analytics/               # Logging and metrics (stub)
│   ├── power/                   # Power monitoring
│   │   ├── base.py              # Abstract power monitor
│   │   └── simulated.py         # Simulated (laptop)
│   │
│   ├── utils/                   # Utilities
│   │   ├── paths.py             # Path resolution
│   │   ├── validation.py        # Input validation
│   │   └── system_checks.py     # Dependency checks
│   │
│   └── tests/                   # Unit tests
│       ├── test_events.py
│       ├── test_state.py
│       ├── test_configuration.py
│       ├── test_braille_models.py
│       ├── test_mode_manager.py
│       └── test_validation.py
```

---

## Testing

```bash
# Run all tests
python -m pytest brailce/tests/ -v

# Run specific test file
python -m pytest brailce/tests/test_events.py -v
```

All tests run on a laptop without physical Raspberry Pi hardware.

---

## Future Raspberry Pi Deployment

When the physical hardware is available:

1. Set `input.device` to `"gpio"` in config.json
2. Set `display.driver` to `"ili9488"` in config.json
3. Configure GPIO pin assignments
4. Install hardware dependencies (`gpiozero`, `spidev`, `Pillow`)
5. The same application pipeline processes events from the GPIO keypad

The logical event flow is identical regardless of input source:

```
Laptop Keyboard  ──┐
                    ├──→ Logical Event → Application Pipeline
GPIO Keypad      ──┘
```

---

## Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Architecture, events, config, input abstraction | ✅ Complete |
| 2 | Braille mapping system, JSON tables | 🔲 Next |
| 3 | Laptop keyboard simulation | 🔲 Planned |
| 4 | Free Input Mode, text buffer, speech | 🔲 Planned |
| 5 | Piper TTS integration | 🔲 Planned |
| 6 | Display abstraction, console display | 🔲 Planned |
| 7 | Ollama interface, AI Assistant Mode | 🔲 Planned |
| 8 | CSV logging, performance timing | 🔲 Planned |
| 9 | Unit and integration tests | 🔲 Planned |
| 10 | Raspberry Pi GPIO keypad | 🔲 Planned |
| 11 | ILI9488 TFT display | 🔲 Planned |
| 12 | Final Raspberry Pi integration | 🔲 Planned |

---

## Troubleshooting

### Piper model or runtime not found
- Install the Python runtime with `pip install piper-tts` or install the Piper CLI.
- Place both `en_US-ryan-medium.onnx` and `en_US-ryan-medium.onnx.json` at the configured model path.
- Run `python tools/speech_check.py` to audition character names, words, sentences, and mode announcements.

### Ollama not responding
- Install from [ollama.ai](https://ollama.ai)
- Start the server: `ollama serve`
- Pull a model: `ollama pull <model_name>`
- Verify: `curl http://127.0.0.1:11434/api/tags`

### keyboard library requires admin/root
- Windows: Run terminal as Administrator
- Linux: Run with `sudo` or add user to the `input` group

---

## License

This is a thesis prototype developed for academic purposes.
