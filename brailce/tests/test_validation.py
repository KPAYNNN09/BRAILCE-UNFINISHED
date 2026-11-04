"""
Brailce Phase 1 Tests – Validation Utilities
================================================

Tests for character validation and AI query validation.
"""

import pytest

from brailce.utils.validation import (
    is_digit,
    is_letter,
    is_math_operator,
    is_punctuation,
    is_supported_character,
    sanitize_character,
    validate_ai_query,
)


class TestCharacterValidation:
    """Tests for character validation functions."""

    def test_letters_are_supported(self) -> None:
        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert is_supported_character(char), f"{char} should be supported"

    def test_lowercase_letters_are_supported(self) -> None:
        for char in "abcdefghijklmnopqrstuvwxyz":
            assert is_supported_character(char), f"{char} should be supported"

    def test_digits_are_supported(self) -> None:
        for char in "0123456789":
            assert is_supported_character(char), f"{char} should be supported"

    def test_math_operators_are_supported(self) -> None:
        for char in "+-*/":
            assert is_supported_character(char), f"{char} should be supported"

    def test_punctuation_is_supported(self) -> None:
        for char in ".,!?':;\"#":
            assert is_supported_character(char), f"{char} should be supported"

    def test_empty_string_not_supported(self) -> None:
        assert not is_supported_character("")

    def test_multi_char_not_supported(self) -> None:
        assert not is_supported_character("AB")

    def test_unsupported_characters(self) -> None:
        for char in "@$%^&()[]{}|\\~`":
            assert not is_supported_character(char), f"{char} should NOT be supported"


class TestCategoryFunctions:
    """Tests for is_letter, is_digit, is_math_operator, is_punctuation."""

    def test_is_letter(self) -> None:
        assert is_letter("A")
        assert is_letter("z")
        assert not is_letter("5")
        assert not is_letter("+")

    def test_is_digit(self) -> None:
        assert is_digit("0")
        assert is_digit("9")
        assert not is_digit("A")

    def test_is_math_operator(self) -> None:
        assert is_math_operator("+")
        assert is_math_operator("-")
        assert is_math_operator("*")
        assert is_math_operator("/")
        assert not is_math_operator("A")

    def test_is_punctuation(self) -> None:
        assert is_punctuation(".")
        assert is_punctuation(",")
        assert not is_punctuation("A")


class TestSanitizeCharacter:
    """Tests for sanitize_character()."""

    def test_lowercase_to_uppercase(self) -> None:
        assert sanitize_character("a") == "A"
        assert sanitize_character("z") == "Z"

    def test_uppercase_unchanged(self) -> None:
        assert sanitize_character("A") == "A"

    def test_digit_unchanged(self) -> None:
        assert sanitize_character("5") == "5"

    def test_unsupported_returns_none(self) -> None:
        assert sanitize_character("@") is None

    def test_empty_returns_none(self) -> None:
        assert sanitize_character("") is None

    def test_multi_char_returns_none(self) -> None:
        assert sanitize_character("AB") is None


class TestAIQueryValidation:
    """Tests for validate_ai_query()."""

    def test_valid_query(self) -> None:
        valid, msg = validate_ai_query("What is Braille?")
        assert valid is True
        assert msg == ""

    def test_empty_query(self) -> None:
        valid, msg = validate_ai_query("")
        assert valid is False
        assert "empty" in msg.lower()

    def test_whitespace_only_query(self) -> None:
        valid, msg = validate_ai_query("   ")
        assert valid is False

    def test_too_short_query(self) -> None:
        valid, msg = validate_ai_query("A")
        assert valid is False
        assert "short" in msg.lower()

    def test_too_long_query(self) -> None:
        valid, msg = validate_ai_query("A" * 1001)
        assert valid is False
        assert "length" in msg.lower() or "exceed" in msg.lower()
