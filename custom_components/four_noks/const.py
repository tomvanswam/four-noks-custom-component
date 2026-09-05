"""Constants for the 4-noks integration."""

from datetime import timedelta
from typing import Final

from homeassistant.const import CONF_SCAN_INTERVAL

DOMAIN: Final = "four_noks"

CONF_CONNECTION: Final = "connection_entry_id"
CONF_UNIT_ID: Final = "unit_id"

DEFAULT_UNIT_ID: Final = 1
DEFAULT_SCAN_INTERVAL: Final = 30

SCAN_INTERVAL: Final = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

