"""
Brailce Tests – Universal OBR Engine
====================================

Tests for OBREngine multi-schema translation:
- Schema 1: "Braille" by braille sight (Direct '#', 'A'..'Z', '0'..'9')
- Schema 2: "Braille" by Prasarnmit demonstration school (6-bit binary dots)
- Schema 3: "Braille Detection" by yapayzeka (Embossed characters)
- Schema 4: Named Roboflow classes (Uradela dataset)
"""

from unittest.mock import MagicMock
import pytest

from brailce.vision.obr_engine import OBREngine


class TestOBREngineLabelDecoder:
    """Test individual cell label decoding across all three recommendation schemas."""

    def test_schema1_direct_characters_and_symbols(self) -> None:
        """Recommendation 1 (braille sight) & Recommendation 3 (yapayzeka)."""
        assert OBREngine.decode_cell_label("#") == "#"
        assert OBREngine.decode_cell_label("^") == "^"
        assert OBREngine.decode_cell_label("A") == "A"
        assert OBREngine.decode_cell_label("z") == "Z"
        assert OBREngine.decode_cell_label("5") == "5"
        assert OBREngine.decode_cell_label(".") == "."
        assert OBREngine.decode_cell_label(",") == ","
        assert OBREngine.decode_cell_label("?") == "?"
        assert OBREngine.decode_cell_label("!") == "!"
        assert OBREngine.decode_cell_label("-") == "-"

    def test_schema2_binary_dots(self) -> None:
        """Recommendation 2 (Prasarnmit demonstration school & DotNeuralNet)."""
        assert OBREngine.decode_cell_label("100000") == "A"
        assert OBREngine.decode_cell_label("110000") == "B"
        assert OBREngine.decode_cell_label("100100") == "C"
        assert OBREngine.decode_cell_label("001111") == "#"  # Number indicator
        assert OBREngine.decode_cell_label("000001") == "^"  # Capital indicator
        assert OBREngine.decode_cell_label("010011") == "."  # Period
        assert OBREngine.decode_cell_label("010000") == ","  # Comma

    def test_schema4_named_classes(self) -> None:
        """Roboflow Uradela named format."""
        assert OBREngine.decode_cell_label("number_sign") == "#"
        assert OBREngine.decode_cell_label("capital") == "^"
        assert OBREngine.decode_cell_label("period") == "."
        assert OBREngine.decode_cell_label("comma") == ","
        assert OBREngine.decode_cell_label("question_mark") == "?"
        assert OBREngine.decode_cell_label("exclamation_mark") == "!"


class TestOBREngineBoxDecoder:
    """Test word reconstruction, space detection, numbers, and capitalization."""

    def test_word_reconstruction_and_spaces(self) -> None:
        """Letters close together form a word; separated letters form multiple words."""
        # "C A T" -> close spacing, "D O G" -> after gap
        boxes = [
            {"x": 50, "y": 100, "w": 30, "h": 40, "name": "C", "conf": 0.9},
            {"x": 85, "y": 100, "w": 30, "h": 40, "name": "A", "conf": 0.9},
            {"x": 120, "y": 100, "w": 30, "h": 40, "name": "T", "conf": 0.9},
            # Gap of 70px (> 30 * 1.30 = 39px)
            {"x": 190, "y": 100, "w": 30, "h": 40, "name": "D", "conf": 0.9},
            {"x": 225, "y": 100, "w": 30, "h": 40, "name": "O", "conf": 0.9},
            {"x": 260, "y": 100, "w": 30, "h": 40, "name": "G", "conf": 0.9},
        ]
        result = OBREngine.decode_boxes(boxes)
        assert result["readable"] is True
        assert result["text"] == "CAT DOG"

    def test_grade1_number_decoding_direct_schema(self) -> None:
        """Recommendation 1 (# + letters -> numbers)."""
        # "#" + "A" + "B" -> "12"
        boxes = [
            {"x": 50, "y": 100, "w": 30, "h": 40, "name": "#", "conf": 0.9},
            {"x": 85, "y": 100, "w": 30, "h": 40, "name": "A", "conf": 0.9},
            {"x": 120, "y": 100, "w": 30, "h": 40, "name": "B", "conf": 0.9},
        ]
        result = OBREngine.decode_boxes(boxes)
        assert result["readable"] is True
        assert result["text"] == "12"

    def test_grade1_number_decoding_binary_schema(self) -> None:
        """Recommendation 2 (Binary number sign 001111 + 100000 + 110000 -> 12)."""
        boxes = [
            {"x": 50, "y": 100, "w": 30, "h": 40, "name": "001111", "conf": 0.9},
            {"x": 85, "y": 100, "w": 30, "h": 40, "name": "100000", "conf": 0.9},
            {"x": 120, "y": 100, "w": 30, "h": 40, "name": "110000", "conf": 0.9},
        ]
        result = OBREngine.decode_boxes(boxes)
        assert result["readable"] is True
        assert result["text"] == "12"

    def test_capitalization_handling(self) -> None:
        """Capital indicator capitalizes subsequent letter."""
        boxes = [
            {"x": 50, "y": 100, "w": 30, "h": 40, "name": "^", "conf": 0.9},
            {"x": 85, "y": 100, "w": 30, "h": 40, "name": "C", "conf": 0.9},
            {"x": 120, "y": 100, "w": 30, "h": 40, "name": "a", "conf": 0.9},
            {"x": 155, "y": 100, "w": 30, "h": 40, "name": "t", "conf": 0.9},
        ]
        result = OBREngine.decode_boxes(boxes)
        assert result["readable"] is True
        assert result["text"] == "CAT"  # or capitalized C

    def test_tilted_paper_line_clustering(self) -> None:
        """Slight vertical variation in Y does not split a word into multiple lines."""
        boxes = [
            {"x": 50, "y": 95, "w": 30, "h": 40, "name": "B", "conf": 0.9},
            {"x": 85, "y": 102, "w": 30, "h": 40, "name": "O", "conf": 0.9},
            {"x": 120, "y": 108, "w": 30, "h": 40, "name": "O", "conf": 0.9},
            {"x": 155, "y": 114, "w": 30, "h": 40, "name": "K", "conf": 0.9},
        ]
        result = OBREngine.decode_boxes(boxes)
        assert result["readable"] is True
        assert result["text"] == "BOOK"


class TestOBREngineSchemaDetection:
    """Test model schema detection."""

    def test_detect_binary_schema(self) -> None:
        engine = OBREngine()
        mock_model = MagicMock()
        mock_model.names = {0: "000000", 1: "100000", 2: "110000", 3: "100100", 4: "001111", 5: "000001"}
        engine._model = mock_model
        assert "binary_dots" in engine._detect_model_schema()

    def test_detect_direct_character_schema(self) -> None:
        engine = OBREngine()
        mock_model = MagicMock()
        mock_model.names = {0: "#", 1: "A", 2: "B", 3: "C", 4: ".", 5: ","}
        engine._model = mock_model
        assert "direct_characters" in engine._detect_model_schema()

    def test_detect_named_class_schema(self) -> None:
        engine = OBREngine()
        mock_model = MagicMock()
        mock_model.names = {0: "number_sign", 1: "capital", 2: "period"}
        engine._model = mock_model
        assert "named_classes" in engine._detect_model_schema()
