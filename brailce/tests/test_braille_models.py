"""
Brailce Phase 1 Tests – Braille Models
=========================================

Tests for BrailleMapping dataclass and CharacterCategory enum.
"""

import pytest

from brailce.braille.models import BrailleMapping, CharacterCategory


class TestBrailleMapping:
    """Tests for BrailleMapping."""

    def test_create_letter_mapping(self) -> None:
        mapping = BrailleMapping(
            character="A",
            display_label="A",
            braille_dots={1},
            braille_unicode="⠁",
            category=CharacterCategory.LETTER,
            speech="A",
        )
        assert mapping.character == "A"
        assert mapping.braille_dots == {1}
        assert mapping.braille_unicode == "⠁"
        assert mapping.category == CharacterCategory.LETTER
        assert mapping.speech == "A"

    def test_create_digit_mapping(self) -> None:
        mapping = BrailleMapping(
            character="1",
            display_label="1",
            braille_dots={1},
            braille_unicode="⠁",
            category=CharacterCategory.DIGIT,
            speech="one",
        )
        assert mapping.character == "1"
        assert mapping.speech == "one"
        assert mapping.category == CharacterCategory.DIGIT

    def test_create_math_mapping(self) -> None:
        mapping = BrailleMapping(
            character="+",
            display_label="+",
            braille_dots={2, 6},
            braille_unicode="⠢",
            category=CharacterCategory.MATH_OPERATOR,
            speech="plus",
        )
        assert mapping.speech == "plus"
        assert mapping.category == CharacterCategory.MATH_OPERATOR

    def test_dots_string_single(self) -> None:
        mapping = BrailleMapping(
            character="A",
            display_label="A",
            braille_dots={1},
        )
        assert mapping.dots_string() == "Dot 1"

    def test_dots_string_multiple(self) -> None:
        mapping = BrailleMapping(
            character="B",
            display_label="B",
            braille_dots={1, 2},
        )
        assert mapping.dots_string() == "Dots 1-2"

    def test_dots_string_empty(self) -> None:
        mapping = BrailleMapping(
            character=" ",
            display_label="Space",
            braille_dots=set(),
        )
        assert mapping.dots_string() == "No dots"

    def test_dots_visual_a(self) -> None:
        """Visual for A (dot 1) should show raised dot at position 1."""
        mapping = BrailleMapping(
            character="A",
            display_label="A",
            braille_dots={1},
        )
        visual = mapping.dots_visual()
        lines = visual.split("\n")
        assert len(lines) == 3
        assert lines[0] == "●○"  # dot 1 raised, dot 4 flat
        assert lines[1] == "○○"  # dot 2 flat, dot 5 flat
        assert lines[2] == "○○"  # dot 3 flat, dot 6 flat

    def test_dots_visual_b(self) -> None:
        """Visual for B (dots 1, 2)."""
        mapping = BrailleMapping(
            character="B",
            display_label="B",
            braille_dots={1, 2},
        )
        visual = mapping.dots_visual()
        lines = visual.split("\n")
        assert lines[0] == "●○"  # dot 1 raised
        assert lines[1] == "●○"  # dot 2 raised
        assert lines[2] == "○○"

    def test_dots_visual_full_cell(self) -> None:
        """Visual with all 6 dots raised."""
        mapping = BrailleMapping(
            character="=",
            display_label="=",
            braille_dots={1, 2, 3, 4, 5, 6},
        )
        visual = mapping.dots_visual()
        lines = visual.split("\n")
        assert lines[0] == "●●"
        assert lines[1] == "●●"
        assert lines[2] == "●●"

    def test_mapping_is_frozen(self) -> None:
        mapping = BrailleMapping(
            character="A",
            display_label="A",
        )
        with pytest.raises(AttributeError):
            mapping.character = "B"  # type: ignore[misc]

    def test_str_representation(self) -> None:
        mapping = BrailleMapping(
            character="A",
            display_label="A",
            braille_dots={1},
            braille_unicode="⠁",
        )
        s = str(mapping)
        assert "A" in s
        assert "Dot 1" in s
        assert "⠁" in s


class TestCharacterCategory:
    """Tests for CharacterCategory enum."""

    def test_all_categories_exist(self) -> None:
        assert CharacterCategory.LETTER is not None
        assert CharacterCategory.DIGIT is not None
        assert CharacterCategory.PUNCTUATION is not None
        assert CharacterCategory.MATH_OPERATOR is not None
        assert CharacterCategory.CONTROL is not None
