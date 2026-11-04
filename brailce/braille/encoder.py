"""
Brailce Braille Encoder
=================================

The encoder performs:
    CHARACTER → BRAILLE REPRESENTATION LOOKUP → SPEECH OUTPUT

This is the primary data-flow direction for the Brailce device.

Note: This is NOT a Braille dot-combination decoder.
The user presses dedicated character buttons; the encoder
associates each character with its Braille representation.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from brailce.braille.mapping import BrailleMappingService
from brailce.braille.models import BrailleMapping

logger = logging.getLogger(__name__)


class BrailleEncoder:
    """
    Encodes characters to their Braille representations.

    Uses the BrailleMappingService for lookups.
    """

    def __init__(self, mapping_service: BrailleMappingService) -> None:
        self._mapping_service = mapping_service

    def encode(self, character: str) -> Optional[BrailleMapping]:
        """
        Encode a single character to its Braille representation.

        Args:
            character: A single character string.

        Returns:
            BrailleMapping if the character is supported, None otherwise.
        """
        if not character:
            return None
        return self._mapping_service.get_mapping(character)

    def encode_text(self, text: str) -> List[Optional[BrailleMapping]]:
        """
        Encode a string of characters to Braille representations.

        Args:
            text: A string of characters.

        Returns:
            List of BrailleMapping objects (None for unsupported characters).
        """
        if not text:
            return []
        return [self.encode(char) for char in text]

    def is_supported(self, character: str) -> bool:
        """Check if a character can be encoded."""
        if not character:
            return False
        return self._mapping_service.is_supported(character)
