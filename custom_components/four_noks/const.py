"""Constants for the 4-noks integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "four_noks"

CONF_UNIT_ID: Final = "unit_id"

DEFAULT_UNIT_ID: Final = 1
DEFAULT_SCAN_INTERVAL: Final = 30

SCAN_INTERVAL: Final = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
