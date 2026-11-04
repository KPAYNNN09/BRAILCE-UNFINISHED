"""
Brailce Unit Tests – Text Normalization and Preprocessor Filter
==============================================================

Verifies the clean normalization rules for Piper Neural TTS:
- Single letters A-Z: lowercase letter with period ("a.", "b.", ..., "z.")
- Digits 0-9: spoken words ("zero.", "one.", ..., "nine.")
- Math & Punctuation: clean English words ("plus.", "minus.", "period.", etc.)
- Words on SPACE/ENTER: trimmed, lowercased, ending with a period (e.g., "apple.")
- Zero phonetic letter respellings
"""

import pytest

from brailce.speech.normalizer import (
    is_keystroke_feedback,
    normalize_for_espeak_character,
    normalize_for_piper,
)


class TestPiperNormalization:
    """Tests for normalize_for_piper."""

    def test_single_characters(self) -> None:
        """Single letters map to explicit names, never bare letter sounds."""
        assert normalize_for_piper("A") == "ay."
        assert normalize_for_piper("B") == "bee."
        assert normalize_for_piper("C") == "see."
        assert normalize_for_piper("Z") == "zee."
        assert normalize_for_piper("a") == "ay."

    def test_digits(self) -> None:
        """Digits 0-9 map to English words."""
        assert normalize_for_piper("0") == "zero."
        assert normalize_for_piper("1") == "one."
        assert normalize_for_piper("5") == "five."
        assert normalize_for_piper("9") == "nine."

    def test_math_operators(self) -> None:
        """Operators map to clean English words."""
        assert normalize_for_piper("+") == "plus."
        assert normalize_for_piper("-") == "minus."
        assert normalize_for_piper("*") == "times."
        assert normalize_for_piper("×") == "times."
        assert normalize_for_piper("/") == "divided by."
        assert normalize_for_piper("÷") == "divided by."
        assert normalize_for_piper("=") == "equals."

    def test_punctuation(self) -> None:
        """Punctuation marks map to clean spoken names."""
        assert normalize_for_piper(".") == "period."
        assert normalize_for_piper(",") == "comma."
        assert normalize_for_piper("?") == "question mark."
        assert normalize_for_piper("!") == "exclamation mark."
        assert normalize_for_piper("#") == "number sign."

    def test_word_normalization_on_space(self) -> None:
        """Completed words on SPACE are trimmed, lowercased, and end with period."""
        assert normalize_for_piper("ARM", is_word=True) == "arm."
        assert normalize_for_piper("CAT", is_word=True) == "cat."
        assert normalize_for_piper("DOG", is_word=True) == "dog."
        assert normalize_for_piper("HELLO", is_word=True) == "hello."
        assert normalize_for_piper("apple", is_word=True) == "apple."

    def test_sentence_normalization_on_enter(self) -> None:
        """Sentences on ENTER are formatted cleanly with terminal punctuation."""
        assert normalize_for_piper("ARMS ARE IMPORTANT") == "Arms are important."
        assert normalize_for_piper("WHAT IS A CAT?") == "What is a cat?"
        assert normalize_for_piper("I LOVE BRAILLE") == "I love braille."

    def test_math_expressions(self) -> None:
        """Expressions are converted to spoken words."""
        assert normalize_for_piper("5 + 3 = 8", is_math=True) == "five plus three equals eight."
        assert normalize_for_piper("9 - 4", is_math=True) == "nine minus four."
        assert normalize_for_piper("4 * 3", is_math=True) == "four times three."
        assert normalize_for_piper("12 / 3", is_math=True) == "12 divided by three."

    def test_markdown_and_ai_stripping(self) -> None:
        """Markdown bold, italics, headers, bullets, and <think> tags stripped."""
        raw = "**Braille** is _great_!\n\n<think>Internal thought</think>\n# Title\n* Bullet item"
        norm = normalize_for_piper(raw)
        assert "Braille is great!" in norm
        assert "<think>" not in norm
        assert "Internal thought" not in norm
        assert "Title" in norm
        assert "Bullet item" in norm


class TestKeystrokeDetection:
    """Tests for is_keystroke_feedback."""

    def test_single_characters(self) -> None:
        assert is_keystroke_feedback("A") is True
        assert is_keystroke_feedback("a") is True
        assert is_keystroke_feedback("5") is True
        assert is_keystroke_feedback("+") is True
        assert is_keystroke_feedback(".") is True

    def test_symbol_names(self) -> None:
        assert is_keystroke_feedback("plus") is True
        assert is_keystroke_feedback("period") is True

    def test_words_not_keystrokes(self) -> None:
        assert is_keystroke_feedback("ARM") is False
        assert is_keystroke_feedback("cat") is False
        assert is_keystroke_feedback("hello") is False
        assert is_keystroke_feedback("WHAT IS A CAT?") is False
