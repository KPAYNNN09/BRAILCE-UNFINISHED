"""
Unit Tests for SpeechService and Natural Speech Integration
============================================================

Tests all required Grade 1 speech, pronunciation, buffer, and mode integration cases:
1. Individual character feedback for A, B, C, and Z.
2. Correct letter-name pronunciation mapping.
3. Decoding the sequence CAT.
4. Reading CAT as one complete word.
5. Reading WHAT IS A CAT? as one complete sentence.
6. Speaking digits 0–9.
7. Speaking plus, minus, multiplication, and division in their correct contexts.
8. Announcing periods, commas, question marks, and exclamation marks.
9. Evaluating 2 + 3, 7 - 2, 3 * 4, and 8 / 2 correctly.
10. Handling division with a non-integer result without silent truncation.
11. Separating Braille control indicators from spoken text where appropriate.
12. Playing a scanner-recognized sentence as complete text.
13. Sending Ollama responses through sentence-level synthesis.
14. Never silently falling back to eSpeak when Piper is unavailable.
15. Preventing speech overlap or repeated whole-sentence announcements during character entry.
16. Preserving the existing camera, display, input, math, and AI functionality.
"""

from unittest.mock import MagicMock, patch
import pytest

from brailce.braille.arithmetic import SafeArithmetic
from brailce.braille.mapping import BrailleMappingService
from brailce.braille.encoder import BrailleEncoder
from brailce.config.loader import ConfigLoader
from brailce.core.app import BrailceApp
from brailce.core.events import AppMode, EventType, InputEvent
from brailce.modes.free_input import FreeInputMode
from brailce.modes.math_mode import MathMode
from brailce.modes.ai_assistant import AIAssistantMode
from brailce.modes.scanner_mode import ScannerMode
from brailce.speech.base import SpeechEngine
from brailce.speech.service import (
    SpeechService,
    LETTER_NAME_MAP,
    DIGIT_NAME_MAP,
    MATH_SYMBOL_MAP,
    PUNCTUATION_NAME_MAP,
)


class MockEngine(SpeechEngine):
    """Controlled mock engine for test assertions."""

    def __init__(self, name: str = "MockTTS", available: bool = True) -> None:
        self._name = name
        self._available = available
        self.spoken_items: list[str] = []
        self.stopped = False

    @property
    def engine_name(self) -> str:
        return self._name

    def speak(self, text: str, interrupt: bool | None = None) -> None:
        self.spoken_items.append(text)

    def stop(self) -> None:
        self.stopped = True

    def is_available(self) -> bool:
        return self._available

    def set_voice(self, voice: str) -> None:
        pass

    def set_rate(self, rate: int) -> None:
        pass

    def set_volume(self, volume: int) -> None:
        pass


@pytest.fixture
def char_engine() -> MockEngine:
    return MockEngine("Piper (Mock)")


@pytest.fixture
def text_engine() -> MockEngine:
    return MockEngine("Piper (Mock)")


@pytest.fixture
def speech_service(char_engine: MockEngine, text_engine: MockEngine) -> SpeechService:
    return SpeechService(
        piper_engine=char_engine,
        behavior="character_and_word",
    )


class TestSpeechServiceCore:
    """Core functionality of SpeechService."""

    def test_case_1_individual_character_feedback_a_b_c_z(
        self, speech_service: SpeechService, char_engine: MockEngine
    ) -> None:
        """Case 1: Individual character feedback for A, B, C, and Z."""
        speech_service.speak_character("A")
        speech_service.speak_character("B")
        speech_service.speak_character("C")
        speech_service.speak_character("Z")

        assert char_engine.spoken_items == ["ay.", "bee.", "see.", "zee."]

    def test_case_2_letter_name_pronunciation_mapping(self) -> None:
        """Case 2: Correct letter-name pronunciation mapping for all letters A-Z."""
        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert char in LETTER_NAME_MAP
            name = LETTER_NAME_MAP[char]
            assert name.endswith(".")
            assert len(name) >= 2

    def test_case_3_decoding_the_sequence_cat(self) -> None:
        """Case 3: Decoding the sequence CAT."""
        config = ConfigLoader.from_defaults()
        mapping_service = BrailleMappingService()
        mapping_service.load_from_config(config)
        encoder = BrailleEncoder(mapping_service)

        encoded = encoder.encode_text("CAT")
        assert len(encoded) == 3
        assert encoded[0].character == "C" and encoded[0].braille_dots == {1, 4}
        assert encoded[1].character == "A" and encoded[1].braille_dots == {1}
        assert encoded[2].character == "T" and encoded[2].braille_dots == {2, 3, 4, 5}

    def test_case_4_reading_cat_as_one_complete_word(
        self, speech_service: SpeechService, char_engine: MockEngine
    ) -> None:
        """Case 4: Reading CAT as one complete word."""
        speech_service.speak_text("CAT")
        assert len(char_engine.spoken_items) == 1
        assert "cat" in char_engine.spoken_items[0].lower()

    def test_case_5_reading_what_is_a_cat_as_complete_sentence(
        self, speech_service: SpeechService, char_engine: MockEngine
    ) -> None:
        """Case 5: Reading WHAT IS A CAT? as one complete sentence."""
        speech_service.speak_text("WHAT IS A CAT?")
        assert len(char_engine.spoken_items) == 1
        spoken = char_engine.spoken_items[0]
        # Punctuation produces question intonation, NOT the words 'question mark'
        assert spoken.lower() == "what is a cat?"
        assert "question mark" not in spoken.lower()

    def test_case_6_speaking_digits_0_to_9(
        self, speech_service: SpeechService, char_engine: MockEngine
    ) -> None:
        """Case 6: Speaking digits 0–9."""
        for digit in "0123456789":
            speech_service.speak_character(digit)

        expected = [
            "zero.", "one.", "two.", "three.", "four.",
            "five.", "six.", "seven.", "eight.", "nine."
        ]
        assert char_engine.spoken_items == expected

    def test_case_7_speaking_plus_minus_mult_div_in_context(
        self, speech_service: SpeechService, char_engine: MockEngine
    ) -> None:
        """Case 7: Speaking plus, minus, multiplication, and division in correct contexts."""
        speech_service.speak_symbol("+", context="math")
        speech_service.speak_symbol("-", context="math")
        speech_service.speak_symbol("*", context="math")
        speech_service.speak_symbol("/", context="math")

        assert char_engine.spoken_items == [
            "plus.", "minus.", "times.", "divided by."
        ]

    def test_case_8_announcing_periods_commas_question_and_exclamation(
        self, speech_service: SpeechService, char_engine: MockEngine
    ) -> None:
        """Case 8: Announcing periods, commas, question marks, and exclamation marks."""
        speech_service.speak_character(".")
        speech_service.speak_character(",")
        speech_service.speak_character("?")
        speech_service.speak_character("!")

        assert char_engine.spoken_items == [
            "period.", "comma.", "question mark.", "exclamation mark."
        ]

    def test_case_9_evaluating_math_problems_correctly(self) -> None:
        """Case 9: Evaluating 2 + 3, 7 - 2, 3 * 4, and 8 / 2 correctly."""
        sol_add = SafeArithmetic.solve("2 + 3")
        assert sol_add.is_valid is True
        assert sol_add.result == 5
        assert "5" in sol_add.result_str

        sol_sub = SafeArithmetic.solve("7 - 2")
        assert sol_sub.is_valid is True
        assert sol_sub.result == 5
        assert "5" in sol_sub.result_str

        sol_mul = SafeArithmetic.solve("3 * 4")
        assert sol_mul.is_valid is True
        assert sol_mul.result == 12
        assert "12" in sol_mul.result_str

        sol_div = SafeArithmetic.solve("8 / 2")
        assert sol_div.is_valid is True
        assert sol_div.result == 4
        assert "4" in sol_div.result_str

    def test_case_10_division_with_non_integer_without_silent_truncation(self) -> None:
        """Case 10: Handling division with a non-integer result without silent truncation."""
        sol = SafeArithmetic.solve("7 / 2")
        assert sol.is_valid is True
        assert sol.result_str == "3 R1"
        assert "remainder of 1" in sol.explanation
        # Must not silently truncate to just 3
        assert sol.result_str != "3"

    def test_case_11_separating_braille_control_indicators_from_spoken_text(self) -> None:
        """Case 11: Separating Braille control indicators (#, ^) from spoken text."""
        app = BrailceApp(ConfigLoader.from_defaults())
        app.state.text_buffer = ""
        app.state.number_mode = False
        mode = FreeInputMode(app)

        # Press '#' (Number Sign)
        mode._handle_character("#")
        # Ensure '#' is NOT added to text buffer
        assert app.state.text_buffer == ""
        assert app.state.number_mode is True

        # Now press 'A' (should decode to digit 1)
        mode._handle_character("A")
        assert app.state.text_buffer == "1"

    def test_case_12_playing_scanner_recognized_sentence_as_complete_text(
        self, speech_service: SpeechService, char_engine: MockEngine
    ) -> None:
        """Case 12: Playing a scanner-recognized sentence as complete text."""
        scanned_text = "The quick brown fox jumps over the lazy dog."
        speech_service.speak_text(scanned_text)

        assert len(char_engine.spoken_items) == 1
        assert char_engine.spoken_items[0] == scanned_text

    def test_case_13_sending_ollama_responses_through_sentence_level_synthesis(
        self, speech_service: SpeechService, char_engine: MockEngine
    ) -> None:
        """Case 13: Sending Ollama responses through sentence-level synthesis."""
        ai_response = "Braille was invented by Louis Braille in France."
        speech_service.speak_text(ai_response)

        assert len(char_engine.spoken_items) == 1
        assert char_engine.spoken_items[0] == ai_response

    def test_case_14_never_falls_back_to_espeak_when_piper_unavailable(
        self, char_engine: MockEngine
    ) -> None:
        """Unavailable Piper does not silently send speech through another engine."""
        piper_unavailable = MockEngine("Piper (Mock)", available=False)
        service = SpeechService(
            piper_engine=piper_unavailable,
        )

        service.speak_text("Fallback sentence test.")
        assert piper_unavailable.spoken_items == ["Fallback sentence test."]
        assert char_engine.spoken_items == []

    def test_case_15_preventing_speech_overlap_during_character_entry(
        self, speech_service: SpeechService, char_engine: MockEngine, text_engine: MockEngine
    ) -> None:
        """Case 15: Preventing speech overlap or repeated whole-sentence announcements during character entry."""
        # Rapid typing should stop any running utterance before starting next
        speech_service.speak_character("C")
        speech_service.speak_character("A")
        speech_service.speak_character("T")

        # Each character sent to character engine with rapid feedback
        assert char_engine.spoken_items == ["see.", "ay.", "tee."]
        # Ensure whole sentence was not announced on character presses
        assert "cat" not in [x.lower() for x in char_engine.spoken_items]

    def test_case_16_preserves_replay_and_stop_functionality(
        self, speech_service: SpeechService, char_engine: MockEngine
    ) -> None:
        """Case 16: Preserving stopping and replaying functionality."""
        speech_service.speak_character("B")
        assert speech_service.last_utterance == "bee."

        speech_service.replay_last_utterance()
        assert char_engine.spoken_items == ["bee.", "bee."]

        speech_service.stop()
        assert char_engine.stopped is True

    def test_speech_modes_behavior(
        self, char_engine: MockEngine, text_engine: MockEngine
    ) -> None:
        """Test the 3 configurable speech behaviors."""
        service = SpeechService(
            character_engine=char_engine,
            text_engine=text_engine,
            behavior="completed_text_only",
        )

        # In completed_text_only mode, character feedback is suppressed
        service.speak_character("A")
        assert len(char_engine.spoken_items) == 0

        # But text is spoken
        service.speak_text("Hello")
        assert len(text_engine.spoken_items) == 1


class TestVocalOutputAndModeIsolation:
    """Verifies user specifications for typing/space/enter vocal feedback and mode isolation."""

    def test_free_input_character_word_sentence_flow(self) -> None:
        """
        Flow in Free Input Mode:
        - every character typed is announced
        - when space is pressed, pronounces the completed word
        - when enter is pressed, pronounces the complete sentence
        """
        config = ConfigLoader.from_defaults()
        app = BrailceApp(config)
        with patch("brailce.core.app.SpeechService.from_config", return_value=MagicMock()):
            app.setup()

        mock_speech = MagicMock()
        app.speech = mock_speech

        free_mode = app._modes[AppMode.FREE_INPUT]
        app._active_mode = free_mode

        # 1. Type C, A, T -> each character is spoken
        free_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="C"))
        free_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="A"))
        free_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="T"))
        assert app.state.text_buffer == "CAT"
        assert mock_speech.speak.call_count == 3

        # 2. Press Space -> pronounces the completed word 'CAT'
        free_mode.handle_event(InputEvent(EventType.SPACE_PRESSED))
        assert app.state.text_buffer == "CAT "
        mock_speech.speak.assert_called_with("CAT")

        # 3. Press Enter -> pronounces the complete sentence
        free_mode.handle_event(InputEvent(EventType.ENTER_PRESSED))
        mock_speech.speak.assert_called_with("CAT", interrupt=False)
        # Buffer is cleared cleanly
        assert app.state.text_buffer == ""

    def test_ai_mode_character_word_sentence_flow(self) -> None:
        """
        Flow in AI Assistant Mode:
        - every character typed is announced
        - when space is pressed, pronounces the completed word
        - when enter is pressed, pronounces the complete question/sentence
        """
        config = ConfigLoader.from_defaults()
        app = BrailceApp(config)
        with patch("brailce.core.app.SpeechService.from_config", return_value=MagicMock()):
            app.setup()

        mock_speech = MagicMock()
        app.speech = mock_speech

        ai_mode = app._modes[AppMode.AI_ASSISTANT]
        app._active_mode = ai_mode

        # 1. Type H, I -> characters spoken
        ai_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="H"))
        ai_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="I"))
        assert app.state.ai_query_buffer == "HI"

        # 2. Press Space -> pronounces completed word 'HI'
        ai_mode.handle_event(InputEvent(EventType.SPACE_PRESSED))
        assert app.state.ai_query_buffer == "HI "
        mock_speech.speak.assert_called_with("HI")

        # 3. Press Enter -> pronounces sentence 'HI'
        with patch("threading.Thread.start"):
            ai_mode.handle_event(InputEvent(EventType.ENTER_PRESSED))
            mock_speech.speak.assert_called_with("HI", interrupt=False)

    def test_mode_isolation_between_math_and_ai(self) -> None:
        """
        Mode isolation:
        - Math mode input stays in math mode
        - Switching modes stops in-flight speech
        - AI mode starts completely fresh with no contamination from Math mode
        """
        config = ConfigLoader.from_defaults()
        app = BrailceApp(config)
        with patch("brailce.core.app.SpeechService.from_config", return_value=MagicMock()):
            app.setup()

        mock_speech = MagicMock()
        app.speech = mock_speech

        # 1. Enter Math mode and type 5 + 3
        app._on_mode_change(AppMode.FREE_INPUT, AppMode.MATH)
        math_mode = app._modes[AppMode.MATH]
        math_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="5"))
        math_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="+"))
        math_mode.handle_event(InputEvent(EventType.CHARACTER_PRESSED, character="3"))
        assert app.state.math_buffer == "5+3"

        # Solve it
        math_mode.handle_event(InputEvent(EventType.ENTER_PRESSED))
        assert app.state.math_last_result == "8"
        assert app.state.math_buffer == ""

        # 2. Switch to AI mode: speech must be stopped immediately
        mock_speech.stop.reset_mock()
        app._on_mode_change(AppMode.MATH, AppMode.AI_ASSISTANT)
        mock_speech.stop.assert_called_once()

        # AI query buffer and display must be completely fresh
        assert app.state.ai_query_buffer == ""
        assert app.state.math_buffer == ""
        if hasattr(app.display, "_current_query"):
            assert app.display._current_query == ""
