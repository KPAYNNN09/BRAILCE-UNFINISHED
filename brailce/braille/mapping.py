"""
Brailce Braille Mapping Service
========================================

Provides character-to-Braille mapping lookups.

Loads mappings from JSON files on initialization.

Example usage:
    mapping_service = BrailleMappingService()
    mapping_service.load_from_config(config)
    result = mapping_service.get_mapping("A")
    # result.braille_dots == {1}
    # result.braille_unicode == "⠁"
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Any

from brailce.braille.models import BrailleMapping, CharacterCategory
from brailce.utils.paths import resolve_path

logger = logging.getLogger(__name__)


class BrailleMappingService:
    """
    Character-to-Braille mapping service.

    Loads mappings from JSON files and provides lookup functions.
    """

    def __init__(self) -> None:
        self._mappings: Dict[str, BrailleMapping] = {}

    def get_mapping(self, character: str) -> Optional[BrailleMapping]:
        """
        Look up the Braille mapping for a character.

        Args:
            character: A single character (e.g. "A", "5", "+").

        Returns:
            BrailleMapping if found, None otherwise.
        """
        return self._mappings.get(character.upper() if character.isalpha() else character)

    def get_dots(self, character: str) -> Optional[set]:
        """Return the Braille dot pattern for a character."""
        mapping = self.get_mapping(character)
        return mapping.braille_dots if mapping else None

    def get_unicode(self, character: str) -> Optional[str]:
        """Return the Unicode Braille character for a character."""
        mapping = self.get_mapping(character)
        return mapping.braille_unicode if mapping else None

    def get_speech_text(self, character: str) -> Optional[str]:
        """Return the speech pronunciation for a character."""
        mapping = self.get_mapping(character)
        return mapping.speech if mapping else None

    def is_supported(self, character: str) -> bool:
        """Check if a character has a Braille mapping."""
        return self.get_mapping(character) is not None

    @property
    def character_count(self) -> int:
        """Return the number of loaded mappings."""
        return len(self._mappings)

    def register_mapping(self, mapping: BrailleMapping) -> None:
        """Register a single mapping (for testing or manual setup)."""
        self._mappings[mapping.character] = mapping

    def load_from_config(self, config: Any) -> None:
        """
        Load mappings from JSON files specified in configuration.

        Args:
            config: A ConfigLoader instance containing a 'braille' section.
        """
        mapping_files: List[str] = config.get("braille", "mapping_files", default=[])
        load_nemeth: bool = config.get("braille", "load_nemeth", default=False)
        
        if load_nemeth:
            nemeth_file = config.get("braille", "nemeth_file")
            if nemeth_file and nemeth_file not in mapping_files:
                mapping_files.append(nemeth_file)

        for file_path in mapping_files:
            self._load_json_file(file_path)

        logger.info(
            "BrailleMappingService loaded %d mappings from %d files.",
            self.character_count,
            len(mapping_files),
        )

    def _load_json_file(self, relative_path: str) -> None:
        """Parse a single JSON mapping file and register its contents."""
        path = resolve_path(relative_path)
        if not path.exists():
            logger.warning("Mapping file not found: %s", path)
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            logger.error("Failed to load mapping file %s: %s", path, exc)
            return

        if not isinstance(data, list):
            logger.error("Mapping file %s must contain a JSON list.", path)
            return

        for entry in data:
            if not isinstance(entry, dict) or "_comment" in entry:
                continue

            try:
                char = entry["character"]
                category_name = entry.get("category", "LETTER").upper()
                try:
                    category = CharacterCategory[category_name]
                except KeyError:
                    category = CharacterCategory.LETTER

                mapping = BrailleMapping(
                    character=char,
                    display_label=entry.get("display_label", char),
                    braille_dots=set(entry.get("braille_dots", [])),
                    braille_unicode=entry.get("braille_unicode", ""),
                    category=category,
                    speech=entry.get("speech", char),
                    nemeth=entry.get("nemeth")
                )
                self.register_mapping(mapping)
            except KeyError as exc:
                logger.warning(
                    "Missing required field in mapping entry from %s: %s",
                    path, exc
                )
