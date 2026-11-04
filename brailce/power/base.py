"""
Brailce Power Monitor – Abstract Base
=======================================

Interface for battery / power status monitoring.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PowerStatus:
    """Current power/battery status."""
    percentage: Optional[int] = None     # 0–100, or None if unknown
    is_charging: Optional[bool] = None
    is_plugged_in: Optional[bool] = None
    status_text: str = "Unknown"


class PowerMonitor(abc.ABC):
    """Abstract interface for power status monitoring."""

    @abc.abstractmethod
    def get_status(self) -> PowerStatus:
        """Return the current power/battery status."""

    @property
    @abc.abstractmethod
    def driver_name(self) -> str:
        """Human-readable name for this power driver."""
