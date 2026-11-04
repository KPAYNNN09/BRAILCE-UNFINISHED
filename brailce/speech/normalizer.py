"""Normalize speech text and route isolated Brailce characters through their names."""

from __future__ import annotations

import re
from typing import Dict

from brailce.speech.pronunciation import (
    CHARACTER_PRONUNCIATIONS,
    is_word_token,
    pronunciation_for,
)

LETTER_NAME_MAP: Dict[str, str] = {
    letter: CHARACTER_PRONUNCIATIONS[letter] for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
}
LETTER_MAP: Dict[str, str] = dict(LETTER_NAME_MAP)
LETTER_MAP.update({letter.lower(): name for letter, name in LETTER_NAME_MAP.items()})
DIGIT_MAP: Dict[str, str] = {
    digit: CHARACTER_PRONUNCIATIONS[digit] for digit in "0123456789"
}
MATH_OPERATORS: Dict[str, str] = {
    symbol: CHARACTER_PRONUNCIATIONS[symbol] for symbol in "+-*/="
}
MATH_OPERATORS.update({"×": "times.", "÷": "divided by."})
PUNCTUATION_MAP: Dict[str, str] = {
    symbol: CHARACTER_PRONUNCIATIONS[symbol]
    for symbol in ".,?!#'\":;"
}
CHARACTER_FILENAME_MAP: Dict[str, str] = {
    symbol: f"char_{name}.wav"
    for symbol, name in {
        "+": "plus",
        "-": "minus",
        "*": "times",
        "/": "divide",
        "=": "equals",
        ".": "period",
        ",": "comma",
        "?": "question",
        "!": "exclamation",
        "#": "hash",
    }.items()
}

_DIGIT_WORDS = tuple(DIGIT_MAP[str(digit)].rstrip(".") for digit in range(10))
_MATH_EXPRESSION = re.compile(r"^\s*(\d+)\s*([+\-*/×÷])\s*(\d+)(?:\s*=\s*(\d+))?\s*$")


def is_keystroke_feedback(text: str) -> bool:
    """Return whether text is one supported character or spoken character name."""
    if not text:
        return False
    clean = text.strip()
    if len(clean) == 1:
        return clean.upper() in CHARACTER_PRONUNCIATIONS
    return clean.upper().rstrip(".") in {
        name.upper().rstrip(".") for name in CHARACTER_PRONUNCIATIONS.values()
    }


def normalize_for_espeak_character(character: str) -> str:
    """Backward-compatible helper; speech is still routed through Piper."""
    return normalize_for_piper(character, is_character=True)


def _spoken_number(number: str) -> str:
    if len(number) == 1:
        return _DIGIT_WORDS[int(number)]
    return number


def _normalize_math_expression(text: str) -> str | None:
    match = _MATH_EXPRESSION.fullmatch(text)
    if not match:
        return None
    left, operator, right, result = match.groups()
    operator_text = MATH_OPERATORS.get(operator) or {
        "×": "times.",
        "÷": "divided by.",
    }[operator]
    parts = [_spoken_number(left), operator_text.rstrip("."), _spoken_number(right)]
    if result is not None:
        parts.extend(("equals", _spoken_number(result)))
    return " ".join(parts) + "."


def normalize_for_piper(
    text: str,
    context: str = "general",
    is_word: bool = False,
    is_math: bool = False,
    is_character: bool = False,
) -> str:
    """Return clean natural-language text, never passing a bare character to Piper."""
    if not text or not text.strip():
        return ""
    raw = text.strip()

    if len(raw) == 1 or is_character:
        spoken = pronunciation_for(raw)
        if spoken:
            return spoken
        if raw in MATH_OPERATORS:
            return MATH_OPERATORS[raw]
        if raw in PUNCTUATION_MAP:
            return PUNCTUATION_MAP[raw]

    math_text = _normalize_math_expression(raw)
    if math_text:
        return math_text

    s = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"```[a-zA-Z]*\n?([\s\S]*?)```", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    s = re.sub(r"__([^_]+)__", r"\1", s)
    s = re.sub(r"_([^_]+)_", r"\1", s)
    s = re.sub(r"^#{1,6}\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*[•*+-]\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*\d+\.\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*>\s*", "", s, flags=re.MULTILINE)
    s = s.replace("×", " times ").replace("÷", " divided by ")
    s = re.sub(r"\s+-\s+", " minus ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return ""

    if is_word or context == "word":
        clean_word = s.strip().lower()
        if not clean_word.endswith((".", "!", "?")):
            clean_word += "."
        return clean_word
    if len(s.split()) == 1:
        return s.lower().rstrip(".") + "."

    if s.isupper():
        s = s.lower()
    s = re.sub(r"\s+([,\.!?])", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s:
        s = s[:1].upper() + s[1:]
        s = re.sub(r"\bi\b", "I", s)
    if s and not s.endswith((".", "!", "?")):
        s += "."
    return s


__all__ = [
    "CHARACTER_FILENAME_MAP",
    "CHARACTER_PRONUNCIATIONS",
    "DIGIT_MAP",
    "LETTER_MAP",
    "LETTER_NAME_MAP",
    "MATH_OPERATORS",
    "PUNCTUATION_MAP",
    "is_keystroke_feedback",
    "is_word_token",
    "normalize_for_espeak_character",
    "normalize_for_piper",
]
