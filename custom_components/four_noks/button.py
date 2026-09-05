"""Button platform for 4-noks action commands."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

try:
    from four_noks_modbus import FourNoksPlug
except ImportError:
    from .vendor.four_noks_modbus import FourNoksPlug

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FourNoksConfigEntry, FourNoksCoordinator
from .entity import FourNoksEntity


@dataclass(frozen=True, kw_only=True)
class FourNoksButtonDescription(ButtonEntityDescription):
    """Describes a 4-noks button entity."""

    press_fn: Callable[[Any], Awaitable[None]]


PLUG_BUTTONS: tuple[FourNoksButtonDescription, ...] = (
    FourNoksButtonDescription(
        key="standby_killer_enable",
        translation_key="standby_killer_enable",
        press_fn=lambda d: d.switch.async_enable_standby_killer(),
    ),
    FourNoksButtonDescription(
        key="data_reset",
        translation_key="data_reset",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda d: d.switch.async_reset_data(),
    ),
    FourNoksButtonDescription(
        key="data_save",
        translation_key="data_save",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda d: d.switch.async_save_data(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourNoksConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up 4-noks buttons."""
    coordinator = entry.runtime_data
    if isinstance(coordinator.device, FourNoksPlug):
        async_add_entities(FourNoksButton(coordinator, desc) for desc in PLUG_BUTTONS)


class FourNoksButton(FourNoksEntity, ButtonEntity):
    """Representation of a 4-noks button action entity."""

    entity_description: FourNoksButtonDescription

    def __init__(
        self,
        coordinator: FourNoksCoordinator,
        description: FourNoksButtonDescription,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Handle button press."""
        await self.entity_description.press_fn(self.coordinator.device)
        await self.coordinator.async_request_refresh()
