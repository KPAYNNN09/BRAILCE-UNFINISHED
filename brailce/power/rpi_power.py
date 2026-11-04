"""
Brailce Raspberry Pi Power & Battery Monitor
===============================================

Monitors battery percentage and charging status for Raspberry Pi.
Supports:
- Waveshare UPS HAT / UPS HAT (B) via I2C (INA219 at 0x41, 0x42, 0x40)
- MAX17048 fuel gauge (0x36)
- Linux standard sysfs (/sys/class/power_supply)
- Fallback: 100% (Plugged directly into USB-C power supply)
"""

from __future__ import annotations

import logging
from typing import Optional

from brailce.power.base import PowerMonitor, PowerStatus

logger = logging.getLogger(__name__)


class PiPowerMonitor(PowerMonitor):
    """
    Hardware battery & power monitor for Raspberry Pi.
    Detects UPS HAT if present; otherwise assumes plugged into 5V power supply (100%).
    """

    def __init__(self) -> None:
        self._bus = None
        self._ups_type: Optional[str] = None
        self._ups_addr: int = 0x41
        self._init_i2c()

    def _init_i2c(self) -> None:
        """Attempt to detect I2C battery management chips (INA219, MAX17048)."""
        try:
            import smbus2
            self._bus = smbus2.SMBus(1)
            # Try INA219 addresses (0x41 Waveshare default, 0x42, 0x40, 0x43)
            for addr in [0x41, 0x42, 0x40, 0x43]:
                try:
                    self._bus.read_byte(addr)
                    self._ups_addr = addr
                    self._ups_type = "ina219"
                    logger.info("Detected UPS HAT (INA219) on I2C address 0x%02X", addr)
                    return
                except Exception:
                    pass

            # Try MAX17048 (0x36)
            try:
                self._bus.read_byte(0x36)
                self._ups_addr = 0x36
                self._ups_type = "max17048"
                logger.info("Detected UPS HAT (MAX17048) on I2C address 0x36")
                return
            except Exception:
                pass
        except Exception as exc:
            logger.debug("I2C power scan failed (smbus2 or I2C unavailable): %s", exc)

    @property
    def driver_name(self) -> str:
        if self._ups_type:
            return f"Raspberry Pi UPS HAT ({self._ups_type.upper()})"
        return "Raspberry Pi USB-C Power (Plugged)"

    def get_status(self) -> PowerStatus:
        """Read current battery/power status."""
        # 1. Read from INA219 UPS HAT
        if self._ups_type == "ina219" and self._bus:
            try:
                raw = self._bus.read_word_data(self._ups_addr, 0x02)
                raw = ((raw << 8) & 0xFF00) | ((raw >> 8) & 0x00FF)
                volts = (raw >> 3) * 0.004
                # Standard dual 18650 in series (8.4V max, 6.4V min) or single cell (4.2V / 3.2V)
                if volts > 5.5:
                    pct = max(0, min(100, int((volts - 6.4) / (8.4 - 6.4) * 100)))
                    charging = volts > 8.2
                else:
                    pct = max(0, min(100, int((volts - 3.2) / (4.2 - 3.2) * 100)))
                    charging = volts > 4.15
                return PowerStatus(
                    percentage=pct,
                    is_charging=charging,
                    is_plugged_in=charging or pct >= 95,
                    status_text=f"UPS: {pct}% ({volts:.2f}V)",
                )
            except Exception as e:
                logger.debug("INA219 read error: %s", e)

        # 2. Read from Linux power_supply sysfs if present
        import os
        try:
            if os.path.exists("/sys/class/power_supply"):
                supplies = os.listdir("/sys/class/power_supply")
                for sup in supplies:
                    cap_file = f"/sys/class/power_supply/{sup}/capacity"
                    stat_file = f"/sys/class/power_supply/{sup}/status"
                    if os.path.exists(cap_file):
                        with open(cap_file, "r") as f:
                            cap = int(f.read().strip())
                        charging = False
                        if os.path.exists(stat_file):
                            with open(stat_file, "r") as f:
                                charging = "charging" in f.read().lower()
                        return PowerStatus(
                            percentage=cap,
                            is_charging=charging,
                            is_plugged_in=True,
                            status_text=f"Battery: {cap}%",
                        )
        except Exception:
            pass

        # 3. Default: Connected directly to AC/USB-C Power Supply
        return PowerStatus(
            percentage=100,
            is_charging=False,
            is_plugged_in=True,
            status_text="Plugged (100%)",
        )
