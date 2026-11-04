# Brailce – Hardware Specifications & Detailed Functional Guide

**Project:** Brailce (Portable Braille-to-Voice Assistive Device)  
**Target User Level:** Grade 1 English Braille Literacy / Primary Special Education (SPED)  
**Operation Environment:** Standalone / 100% Offline (No Internet Required)  

---

## 1. Hardware Specifications (Bill of Materials)

The Brailce device is built around a dedicated single-board computer architecture designed for embedded machine learning, real-time audio synthesis, and hardware-level tactile feedback.

| Component | Model / Specification | Purpose & Function |
| :--- | :--- | :--- |
| **Main Compute Unit** | **Raspberry Pi 5** (4GB / 8GB RAM) | Central processing unit. Powers the Linux OS, executes the Python 3 application pipeline, hosts the local Ollama LLM server, and runs the YOLOv8 Optical Braille Recognition model. |
| **Tactile Keypad** | **Dedicated Character Keypad with Embossed Braille Keycaps** | Primary physical input. Each key possesses an embossed 6-dot Braille cell label representing an English letter ($A\text{–}Z$), digit ($0\text{–}9$), punctuation mark, math operator, or control key. Connected via Raspberry Pi GPIO pins or I2C GPIO expander (e.g., MCP23017). *(Simulated via keyboard during development).* |
| **Camera Module** | **Raspberry Pi Camera Module (v2 / v3)** or standard UVC USB Camera | Captures high-resolution images of physical embossed Braille sheets, flashcards, and printed textbooks for real-time Optical Braille Recognition. |
| **Visual Display** | **3.5-inch TFT LCD Display** (480×320, SPI, **ILI9488**) | Serves sighted instructors, SPED teachers, and evaluators. Displays the active mode, real-time Braille cell graphics (dot matrix), text buffer, and system alerts. *(Simulated via ConsoleDisplay during development).* |
| **Audio Output** | **Mini Speaker / 3.5mm Audio Output / I2S DAC Amplifier** (e.g., MAX98357A) | Provides immediate, non-overlapping voice feedback via **eSpeak NG** Text-to-Speech (TTS) for individual key presses, completed words, scanned pages, and AI responses. |
| **Power System** | **5V / 5A USB-C Battery Pack / Power Bank** or LiPo UPS Power HAT | Delivers portable, rechargeable, cord-free power for continuous classroom use. |
| **Storage** | **MicroSD Card (64GB+ Class 10 / A2 High Speed)** | Houses the operating system, TTS phonetic dictionaries, Ollama model weights (`LiquidAI`), and the YOLOv8 model file (`yolov8_braille.pt`). |

---

## 2. High-Level Architecture & Operating Modes

Brailce operates across four distinct modes, toggled cyclically using the physical **MODE** key:

```
                                  ┌──────────────────────────┐
                                  │   BRAILCE DEVICE MODES   │
                                  └─────────────┬────────────┘
         ┌──────────────────────────────┼──────────────────────────────┬──────────────────────────────┐
         ▼                              ▼                              ▼                              ▼
  [ FREE INPUT MODE ]            [ MATH MODE ]               [ AI ASSISTANT MODE ]          [ SCANNER MODE ]
  • Letter-by-letter typing      • Grade 1 DepEd math        • Offline educational tutor    • OBR camera capture
  • Word pronunciation on space  • Step-by-step counting     • Voice answers in <2 sentences• Readability checks
  • Sentence reading on Enter    • Offline SafeArithmetic    • Friendly & encouraging tone  • Manual read confirmation
```

---

## 3. Granular List of Functions (Function by Function)

### Section A: Free Input Mode (Braille Literacy & Typing Practice)

#### Function 1: Character Input & Real-Time Encoding (`_handle_character`)
* **Trigger:** Pressing any physical embossed key ($A\text{–}Z$, $0\text{–}9$, punctuation, math symbols).
* **Internal Process:** Looks up the character in the mapping database, resolves its exact 6-dot Braille pattern and Unicode glyph, and appends the character to the active text buffer.
* **Output:**
  * **Audio:** Speaks the character name immediately via eSpeak TTS.
  * **Display:** Renders the character, updates the buffer string, and displays the dot numbers (e.g., *"Dots 1, 4"* for C) alongside a graphical 6-dot cell.

#### Function 2: Word Completion & Automatic Pronunciation (`_handle_space`)
* **Trigger:** Pressing the **SPACE** key.
* **Internal Process:** Parses the word just completed before the space and appends a space character to the text buffer.
* **Output:**
  * **Audio:** Speaks the full completed word aloud (e.g., typing `B` $\rightarrow$ `O` $\rightarrow$ `O` $\rightarrow$ `K` followed by **SPACE** causes the device to speak *"book"*).
  * **Display:** Updates the LCD buffer with the space separator.

#### Function 3: Full Sentence Playback (`_handle_enter`)
* **Trigger:** Pressing the **ENTER** key while in Free Input Mode.
* **Internal Process:** Retrieves the complete accumulated text buffer.
* **Output:**
  * **Audio:** Speaks the entire accumulated sentence or passage aloud. If the buffer is empty, speaks *"Buffer empty"*.
  * **Display:** Refreshes the display view.

#### Function 4: Character Deletion / Backspace (`_handle_backspace`)
* **Trigger:** Pressing the **BACKSPACE** key.
* **Internal Process:** Removes the most recently entered character from the buffer.
* **Output:**
  * **Audio:** Speaks *"Backspace"*.
  * **Display:** Updates the display buffer to reflect the deleted character.

#### Function 5: Buffer Clear / Reset (`_handle_clear`)
* **Trigger:** Pressing the **CLEAR** key.
* **Internal Process:** Wipes the entire text buffer clean back to an empty state.
* **Output:**
  * **Audio:** Speaks *"Buffer cleared"*.
  * **Display:** Resets the buffer line on the LCD.

---

### Section B: Math Mode (Grade 1 DepEd Arithmetic & Counting Explanations – Method 1)

#### Function 6: Math Digit & Operator Input (`_handle_character`)
* **Trigger:** Pressing physical keys for digits ($0\text{–}9$) or math operators (`+`, `-`, `*`, `/`).
* **Internal Process:**
  * Validates characters against permitted math input set.
  * Rejects alphabetical letters with immediate voice guidance: *"Numbers only"*.
  * Updates the internal math buffer (`math_buffer`) and refreshes the LCD display.
* **Output:**
  * **Audio:** Speaks the digit or operator name immediately (e.g., *"five"*, *"plus"*, *"three"*).
  * **Display:** Shows the character, Braille dot pattern, and accumulated equation buffer.

#### Function 7: Deterministic Step-by-Step Counting Solver (`SafeArithmetic.solve`)
* **Trigger:** Pressing **ENTER** or the equals (`=`) key.
* **Internal Process:**
  * Parses expression into numbers and operators safely without `eval()` or `exec()`.
  * Generates pedagogical, auditory step-by-step counting explanations adhering strictly to the **Grade 1 DepEd Mathematics Curriculum**:
    1. **Addition ("Counting On"):**
       * For $5 + 3$: *"5 plus 3 equals 8. Let's count together! Start at 5, and count up 3 more: 6, 7, 8. The answer is 8."*
       * Adding zero ($A + 0$): *"Adding zero leaves A unchanged! The answer is A."*
       * Adding one ($A + 1$): *"Count up 1 more from A: answer."*
       * Two-digit addition ($14 + 23$): Solves by place value (ones then tens) matching DepEd Q3/Q4 competencies.
    2. **Subtraction ("Counting Back"):**
       * For $9 - 4$: *"9 minus 4 equals 5. Let's count back! Start at 9, and count back 4: 8, 7, 6, 5. The answer is 5."*
       * Subtracting zero / same number ($A - 0$, $A - A$): Zero property explained clearly.
       * Grade 1 Whole-Number Underflow Constraint: If a learner inputs $3 - 5$, the device rejects negative numbers with: *"In Grade 1 math, we cannot take away 5 from 3 because 5 is bigger than 3."*
    3. **Multiplication (Repeated Addition):** Explains as repeated groups (e.g., $3 \times 2 \rightarrow$ *"3 groups of 2: 2 plus 2 plus 2 equals 6"*).
    4. **Division (Equal Sharing):** Explains as sharing equally with quotients and remainders; explicitly rejects division by zero.
* **Output:**
  * **Audio:** eSpeak synthesizes the full step-by-step counting explanation aloud.
  * **Display:** Shows the Math Solution card featuring the equation, answer, Braille dots for the answer, and compact step summary (e.g. `Start 5 -> 6, 7, 8`).
  * **State:** Clears `math_buffer` so student is immediately ready for the next problem.

#### Function 8: Math Buffer Backspace & Clear (`_handle_backspace`, `_handle_clear`)
* **Trigger:** Pressing **BACKSPACE** or **CLEAR** while in Math Mode.
* **Internal Process:** Deletes the last operator/digit or clears the entire math buffer.
* **Output:** Speaks *"backspace"* or *"cleared"* and refreshes the LCD display.

---

### Section C: AI Assistant Mode (Interactive Voice Tutor)

#### Function 9: Question Formulation & Prompt Buffering
* **Trigger:** Typing characters using the embossed Braille keys while in AI Assistant Mode.
* **Internal Process:** Accumulates the student's question in a dedicated prompt buffer while maintaining immediate auditory feedback for each key.
* **Display:** Displays the incoming question in the AI prompt area.

#### Function 10: Offline AI Query Processing (`_query_ai`)
* **Trigger:** Pressing **ENTER** after typing a question.
* **Internal Process:**
  1. Announces *"Thinking..."* to indicate processing.
  2. Submits the prompt to the on-device Ollama inference server running `LiquidAI/lfm2.5-1.2b-instruct`.
  3. Applies pedagogical system prompt constraints: answers must be accurate, emotionally supportive, easy to understand for young learners, and under two sentences.
* **Connectivity:** 100% offline; requires no internet connection or external API.

#### Function 11: AI Voice Response Delivery
* **Trigger:** Completion of local LLM inference.
* **Internal Process:** Streams and enqueues the generated response into the eSpeak TTS queue.
* **Output:**
  * **Audio:** Reads the educational explanation aloud through the speaker.
  * **Display:** Shows the full AI answer on the screen for the instructor.

#### Function 12: Query Reset / Cancellation
* **Trigger:** Pressing **CLEAR** while composing an AI query.
* **Internal Process:** Discards the active prompt buffer so the student can formulate a new inquiry.

---

### Section D: Scanner Mode (Optical Braille Recognition / Talking Reader)

#### Function 13: Live Camera Viewfinder & Aiming Preview (`_preview_loop`)
* **Trigger:** Entering Scanner Mode.
* **Internal Process:** Spawns a background preview thread that continuously streams camera frames (~25 FPS) directly to the visual display (ILI9488 TFT LCD / OpenCV window). Overlays green alignment guidelines, center crosshairs, and status instructions.
* **Benefit for Sighted Users:** Enables non-blind assistants and SPED teachers to accurately see where the device/camera is positioned over the physical Braille document before scanning.

#### Function 14: Scan Initiation (`_start_scan`)
* **Trigger:** Pressing **ENTER** when prompted with *"Position Braille inside box | Press Enter to Scan"*.
* **Internal Process:** Captures the current image frame and feeds it into the OBR deep learning pipeline.
* **Output:** Speaks *"Scanning document"* and displays *"Scanning document with AI..."* on the screen.

#### Function 15: Real-Time Braille Cell Detection (OBR YOLOv8 Engine)
* **Internal Process:** The local YOLOv8 neural network (`yolov8_braille.pt`) detects bounding boxes of physical 6-dot Braille cells and classifies each cell into a 6-bit binary pattern.

#### Function 16: Spatial Layout & Line Reconstruction
* **Internal Process:** 
  1. Groups detected cells vertically based on Y-coordinates into distinct text lines.
  2. Sorts cells horizontally along each line from left to right.
  3. Measures horizontal inter-cell distances to reconstruct spaces between words automatically.

#### Function 17: Uncontracted Braille Translation
* **Internal Process:** Translates detected binary cell configurations into standard English text:
  * English Alphabet: Letters $A\text{–}Z$
  * Digits $0\text{–}9$: Detects the Number Indicator (`#` / `⠼`) and decodes continuous multi-digit numbers (e.g., `#be` $\rightarrow$ `25`)
  * Punctuation Marks: Periods (`.`), commas (`,`), question marks (`?`), exclamation points (`!`), hyphens (`-`), apostrophes (`'`), colons (`:`), and semicolons (`;`)
  * Capitalization: Detects the Capital Indicator (Dot 6, `⠠`) and capitalizes the subsequent letter

#### Function 18: Readability Check & Confirmation Prompt
* **Internal Process:** Verifies that a sufficient number of legible Braille cells were detected.
* **Output:**
  * **If illegible/unreadable:** Displays and speaks *"Not enough braille detected. Please adjust camera."* (returns to live preview for realignment).
  * **If readable:** Announces *"Document successfully scanned. Press Enter to hear it."* and displays *"Document Scanned! Press Enter to Read."* along with the recognized text buffer. Requires the user to explicitly confirm before reading aloud.

#### Function 19: Scanned Document Voice Playback (`_speak_result`)
* **Trigger:** Pressing **ENTER** after a successful scan.
* **Internal Process:** Enqueues the complete translated text into the TTS engine.
* **Output:** 
  * **Audio:** Reads the entire scanned text aloud through the speaker.
  * **Display:** Shows *"Reading..."* and displays the full text on the LCD.

#### Function 20: Scanner Reset
* **Trigger:** Pressing **CLEAR** while in Scanner Mode.
* **Internal Process:** Clears stored scan results and returns the scanner to the ready state (*"Position Braille inside box | Press Enter to Scan"*).

---

### Section E: System, Display & Control Functions

#### Function 21: Cyclic Mode Switching (`toggle_mode`)
* **Trigger:** Pressing the physical **MODE** button.
* **Internal Process:** Cycles sequentially between:
  $$\text{Free Input Mode} \longrightarrow \text{Math Mode} \longrightarrow \text{AI Assistant Mode} \longrightarrow \text{Scanner Mode} \longrightarrow \text{Free Input Mode}$$
* **Output:** Speaks the new mode name aloud (e.g., *"Math Mode"*) and updates the LCD header.

#### Function 22: Dual-Audience Visual Rendering (ILI9488 TFT / Console)
* **Internal Process:** Real-time visual interface rendering designed specifically so sighted educators can assist visually impaired pupils:
  * Current mode indicator
  * Accumulated text buffer / math buffer
  * Focused Braille character name and Unicode glyph
  * Dot positions list (e.g., `(1, 4)`)
  * Graphical 6-dot matrix cell ($3 \times 2$ grid)
  * Math solution card with step-by-step counting steps
  * System status messages and diagnostic alerts

#### Function 23: Non-Blocking Audio Queue Management (`EspeakEngine`)
* **Internal Process:** Maintains an asynchronous background speech queue (`Queue(maxsize=50)`).
* **Benefit:** Eliminates audio clipping, stuttering, and dropped syllables during rapid key entry.

#### Function 24: Hardware Volume Control
* **Trigger:** Pressing Volume Up / Volume Down controls.
* **Internal Process:** Dynamically adjusts the software audio gain level.

#### Function 25: Pre-Flight System Diagnostics (`run_all_checks`)
* **Trigger:** System initialization on boot.
* **Internal Process:** Performs integrity checks on:
  * eSpeak NG installation and voice availability
  * Local Ollama server status and model loading
  * Camera device connectivity
  * JSON Braille mapping table validation
* **Output:** Displays warning messages on screen and logs errors if any subsystem requires attention.

#### Function 26: Educational Session Analytics & Data Logging (`AnalyticsLogger`)
* **Internal Process:** Automatically generates timestamped session logs in CSV format recording:
  * Keypress timestamps and character accuracy
  * Mode change events
  * Math problems solved and explanations generated
  * AI query prompts and generation latencies
  * Scanned document events
* **Benefit:** Provides SPED educators and thesis researchers with empirical data to track student learning progress and typing proficiency over time.
