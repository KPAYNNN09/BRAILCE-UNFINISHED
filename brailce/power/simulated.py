"""
Brailce Simulated Power Monitor – Laptop Development
======================================================

Returns UNKNOWN for all power metrics when running on a laptop
without Raspberry Pi battery hardware.

The software must NOT fabricate battery percentages.
"""

from __future__ import annotations

import logging

from brailce.power.base import PowerMonitor, PowerStatus

logger = logging.getLogger(__name__)


class SimulatedPowerMonitor(PowerMonitor):
    """
    Simulated power monitor for laptop development.

    Always reports status as "Unknown" since there is no
    Raspberry Pi battery hardware connected.
    """

    @property
    def driver_name(self) -> str:
        return "Simulated Power Monitor (No Hardware)"

    def get_status(self) -> PowerStatus:
        """Return unknown power status."""
        return PowerStatus(
            percentage=None,
            is_charging=None,
            is_plugged_in=None,
            status_text="Unknown (simulation mode)",
        )
