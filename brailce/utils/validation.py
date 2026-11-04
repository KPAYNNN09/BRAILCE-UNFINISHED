"""
Brailce Utility – Validation
===============================

Input validation helpers used across the application.
"""

from __future__ import annotations

from typing import Optional, Set

# Characters supported by the dedicated character keypad
VALID_LETTERS: Set[str] = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
VALID_DIGITS: Set[str] = set("0123456789")
VALID_MATH_OPERATORS: Set[str] = {"+", "-", "*", "/"}
VALID_PUNCTUATION: Set[str] = {".", ",", "!", "?", "'", '"', ":", ";", "#"}
VALID_CHARACTERS: Set[str] = (
    VALID_LETTERS | VALID_DIGITS | VALID_MATH_OPERATORS | VALID_PUNCTUATION
)


def is_supported_character(char: str) -> bool:
    """
    Check if a character is supported by the Brailce keypad.

    Args:
        char: A single character string.

    Returns:
        True if the character has a dedicated button on the keypad.
    """
    if not char or len(char) != 1:
        return False
    return char.upper() in VALID_CHARACTERS


def is_letter(char: str) -> bool:
    """Check if a character is a supported letter (A–Z)."""
    return len(char) == 1 and char.upper() in VALID_LETTERS


def is_digit(char: str) -> bool:
    """Check if a character is a supported digit (0–9)."""
    return len(char) == 1 and char in VALID_DIGITS


def is_math_operator(char: str) -> bool:
    """Check if a character is a supported math operator."""
    return len(char) == 1 and char in VALID_MATH_OPERATORS


def is_punctuation(char: str) -> bool:
    """Check if a character is supported punctuation."""
    return len(char) == 1 and char in VALID_PUNCTUATION


def sanitize_character(char: str) -> Optional[str]:
    """
    Normalize and validate a character for the Brailce keypad.

    Converts lowercase letters to uppercase.
    Returns None if the character is not supported.
    """
    if not char or len(char) != 1:
        return None
    upper = char.upper() if char.isalpha() else char
    if upper in VALID_CHARACTERS:
        return upper
    return None


import re


def is_multi_digit_math_query(query: str) -> bool:
    """
    Check if a query is a math-related question containing multi-digit numbers (> 9).
    Brailce AI Assistant enforces single-digit arithmetic only (0 to 9).
    """
    q = query.lower()
    has_math_op = any(op in q for op in ["+", "-", "*", "/", "="])
    has_math_kw = bool(
        re.search(
            r"\b(plus|minus|times|divided|divide|add|subtract|multiply|sum|difference|product|equals|math|calculate)\b",
            q,
        )
    )
    has_multi_num = bool(re.search(r"\b\d{2,}\b", q))
    has_multi_word = bool(
        re.search(
            r"\b(ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)\b",
            q,
        )
    )
    return (has_math_op or has_math_kw) and (has_multi_num or has_multi_word)


def validate_ai_query(query: str) -> tuple[bool, str]:
    """
    Validate an AI assistant query.

    Args:
        query: The text to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    stripped = query.strip()
    if not stripped:
        return False, "Query is empty."
    if len(stripped) < 2:
        return False, "Query is too short."
    if len(stripped) > 1000:
        return False, "Query exceeds maximum length (1000 characters)."
    if is_multi_digit_math_query(stripped):
        return False, "In AI mode, math questions must be single digits only (0 to 9)."
    return True, ""

