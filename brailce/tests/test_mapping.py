"""
Brailce Phase 2 Tests – Braille Mapping
==========================================

Tests for Braille mapping files, mapping service JSON loading,
and the encoder.
"""

import json
import tempfile
from pathlib import Path
import pytest

from brailce.braille.encoder import BrailleEncoder
from brailce.braille.mapping import BrailleMappingService
from brailce.braille.models import BrailleMapping, CharacterCategory
from brailce.config.loader import ConfigLoader


class TestBrailleMappingService:
    """Tests for the mapping service loading and lookups."""

    @pytest.fixture
    def mock_config(self) -> ConfigLoader:
        """Create a mock config that points to test mapping files."""
        # Use the actual default config, which points to the mappings we created
        return ConfigLoader.from_defaults()

    def test_load_real_mappings_from_config(self, mock_config: ConfigLoader) -> None:
        """Test loading the real JSON mappings we created in Phase 2."""
        service = BrailleMappingService()
        service.load_from_config(mock_config)
        
        # We created 26 letters + 10 digits + 9 punctuation (incl. #) + 5 math (+, -, *, /, =) = 50 mappings
        assert service.character_count == 50

        # Test equals mapping
        eq_mapping = service.get_mapping("=")
        assert eq_mapping is not None
        assert eq_mapping.speech == "equals"

        # Test # number indicator mapping
        hash_mapping = service.get_mapping("#")
        assert hash_mapping is not None
        assert hash_mapping.braille_dots == {3, 4, 5, 6}
        assert hash_mapping.braille_unicode == "⠼"
        assert hash_mapping.speech == "number sign"

        # Test some specific lookups
        a_mapping = service.get_mapping("A")
        assert a_mapping is not None
        assert a_mapping.braille_dots == {1}
        assert a_mapping.speech == "A"
        assert a_mapping.category == CharacterCategory.LETTER

        digit_1 = service.get_mapping("1")
        assert digit_1 is not None
        assert digit_1.braille_dots == {2}
        assert digit_1.speech == "one"
        assert digit_1.category == CharacterCategory.DIGIT
        
        math_plus = service.get_mapping("+")
        assert math_plus is not None
        assert math_plus.braille_dots == {3, 4, 6}
        assert math_plus.speech == "plus"
        assert math_plus.category == CharacterCategory.MATH_OPERATOR

    def test_get_dots(self) -> None:
        service = BrailleMappingService()
        mapping = BrailleMapping("A", "A", {1})
        service.register_mapping(mapping)
        
        assert service.get_dots("A") == {1}
        assert service.get_dots("B") is None

    def test_get_unicode(self) -> None:
        service = BrailleMappingService()
        mapping = BrailleMapping("A", "A", braille_unicode="⠁")
        service.register_mapping(mapping)
        
        assert service.get_unicode("A") == "⠁"

    def test_get_speech_text(self) -> None:
        service = BrailleMappingService()
        mapping = BrailleMapping("+", "Plus", speech="plus")
        service.register_mapping(mapping)
        
        assert service.get_speech_text("+") == "plus"

    def test_is_supported(self) -> None:
        service = BrailleMappingService()
        mapping = BrailleMapping("A", "A")
        service.register_mapping(mapping)
        
        assert service.is_supported("A") is True
        assert service.is_supported("B") is False


class TestBrailleEncoder:
    """Tests for the Braille encoder layer."""

    @pytest.fixture
    def encoder(self) -> BrailleEncoder:
        service = BrailleMappingService()
        service.register_mapping(BrailleMapping("A", "A", {1}, "⠁", speech="A"))
        service.register_mapping(BrailleMapping("B", "B", {1, 2}, "⠃", speech="B"))
        service.register_mapping(BrailleMapping("C", "C", {1, 4}, "⠉", speech="C"))
        return BrailleEncoder(service)

    def test_encode_single_character(self, encoder: BrailleEncoder) -> None:
        result = encoder.encode("A")
        assert result is not None
        assert result.character == "A"
        assert result.braille_dots == {1}

    def test_encode_unsupported_character(self, encoder: BrailleEncoder) -> None:
        result = encoder.encode("Z")
        assert result is None

    def test_encode_text(self, encoder: BrailleEncoder) -> None:
        results = encoder.encode_text("ABC")
        assert len(results) == 3
        assert results[0] is not None and results[0].character == "A"
        assert results[1] is not None and results[1].character == "B"
        assert results[2] is not None and results[2].character == "C"

    def test_encode_text_with_unsupported(self, encoder: BrailleEncoder) -> None:
        results = encoder.encode_text("ABZ")
        assert len(results) == 3
        assert results[0] is not None and results[0].character == "A"
        assert results[1] is not None and results[1].character == "B"
        assert results[2] is None
        
    def test_is_supported(self, encoder: BrailleEncoder) -> None:
        assert encoder.is_supported("A") is True
        assert encoder.is_supported("Z") is False
        assert encoder.is_supported("") is False
