"""
Brailce Braille Data Models
=============================

Data structures representing Braille character mappings.

Each supported character has a BrailleMapping that stores:
    - The character itself
    - Its display label
    - The Braille dot pattern (e.g. {1} for A, {1, 2} for B)
    - Unicode Braille representation
    - Category (letter, digit, punctuation, math, control)
    - Speech pronunciation
    - Optional Nemeth mathematical notation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Set


class CharacterCategory(Enum):
    """Classification of a mapped character."""
    LETTER = auto()
    DIGIT = auto()
    PUNCTUATION = auto()
    MATH_OPERATOR = auto()
    CONTROL = auto()


@dataclass(frozen=True)
class BrailleMapping:
    """
    Complete mapping of a single character to its Braille representation.

    Attributes:
        character:       The character this mapping represents (e.g. "A", "5", "+").
        display_label:   Human-readable label for display purposes.
        braille_dots:    Set of dot numbers in the Braille cell (1–6).
        braille_unicode: Unicode Braille character (e.g. "⠁" for A).
        category:        Classification of the character.
        speech:          Spoken name for the configured Piper speech pipeline.
        nemeth:          Optional Nemeth Braille representation for math contexts.
    """
    character: str
    display_label: str
    braille_dots: Set[int] = field(default_factory=set)
    braille_unicode: str = ""
    category: CharacterCategory = CharacterCategory.LETTER
    speech: str = ""
    nemeth: Optional[str] = None

    def dots_string(self) -> str:
        """
        Return a human-readable dot-number string.

        Example:
            {1, 2} → "Dots 1-2"
            {1}    → "Dot 1"
        """
        if not self.braille_dots:
            return "No dots"
        sorted_dots = sorted(self.braille_dots)
        if len(sorted_dots) == 1:
            return f"Dot {sorted_dots[0]}"
        return "Dots " + "-".join(str(d) for d in sorted_dots)

    def dots_visual(self) -> str:
        """
        Return a 3-row × 2-column visual representation of the Braille cell.

        Uses ● for raised dots and ○ for flat dots.

        Dot positions:
            1 4
            2 5
            3 6

        Example for "A" (dot 1):
            ●○
            ○○
            ○○
        """
        def _dot(n: int) -> str:
            return "●" if n in self.braille_dots else "○"

        return (
            f"{_dot(1)}{_dot(4)}\n"
            f"{_dot(2)}{_dot(5)}\n"
            f"{_dot(3)}{_dot(6)}"
        )

    def __str__(self) -> str:
        return (
            f"BrailleMapping('{self.character}' | "
            f"{self.dots_string()} | "
            f"Unicode: {self.braille_unicode})"
        )
