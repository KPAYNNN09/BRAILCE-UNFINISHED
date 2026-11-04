"""Canonical spoken names for supported Brailce input characters."""

from __future__ import annotations

from typing import Dict, FrozenSet

CHARACTER_PRONUNCIATIONS: Dict[str, str] = {
    "A": "ay.",
    "B": "bee.",
    "C": "see.",
    "D": "dee.",
    "E": "ee.",
    "F": "eff.",
    "G": "jee.",
    "H": "aitch.",
    "I": "eye.",
    "J": "jay.",
    "K": "kay.",
    "L": "el.",
    "M": "em.",
    "N": "en.",
    "O": "oh.",
    "P": "pee.",
    "Q": "cue.",
    "R": "ar.",
    "S": "ess.",
    "T": "tee.",
    "U": "you.",
    "V": "vee.",
    "W": "double you.",
    "X": "ex.",
    "Y": "why.",
    "Z": "zee.",
    "0": "zero.",
    "1": "one.",
    "2": "two.",
    "3": "three.",
    "4": "four.",
    "5": "five.",
    "6": "six.",
    "7": "seven.",
    "8": "eight.",
    "9": "nine.",
    "+": "plus.",
    "-": "minus.",
    "*": "times.",
    "/": "divided by.",
    "=": "equals.",
    ".": "period.",
    ",": "comma.",
    "?": "question mark.",
    "!": "exclamation mark.",
    "#": "number sign.",
    "'": "apostrophe.",
    '"': "quote.",
    ":": "colon.",
    ";": "semicolon.",
}

CHARACTERS_TO_PRONOUNCE: FrozenSet[str] = frozenset(CHARACTER_PRONUNCIATIONS)


def pronunciation_for(character: str) -> str:
    """Return the canonical spoken form of one supported character."""
    return CHARACTER_PRONUNCIATIONS.get(character.upper(), "")


def is_word_token(token: str) -> bool:
    """Treat alphabetic tokens with a vowel as words; spell consonant-only tokens."""
    letters = token.lower().replace("'", "").replace("-", "")
    return bool(letters) and letters.isalpha() and any(
        character in "aeiouy" for character in letters
    )


def spelled_pronunciations(token: str) -> list[str]:
    """Return character-name pronunciations for a mixed or non-word token."""
    return [
        pronunciation_for(character)
        for character in token
        if pronunciation_for(character)
    ]
