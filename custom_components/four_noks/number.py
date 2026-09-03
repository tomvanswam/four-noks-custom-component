"""Number platform for 4-noks device configuration settings."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

try:
    from four_noks_modbus import FourNoksDevice, FourNoksGateway, FourNoksPlug
except ImportError:
    from .vendor.four_noks_modbus import FourNoksDevice, FourNoksGateway, FourNoksPlug

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FourNoksConfigEntry, FourNoksCoordinator
from .entity import FourNoksEntity


@dataclass(frozen=True, kw_only=True)
class FourNoksNumberDescription(NumberEntityDescription):
    """Describes a 4-noks number entity."""

    value_fn: Callable[[FourNoksDevice], float | None]
    set_value_fn: Callable[[FourNoksDevice, float], Awaitable[None]]


PLUG_NUMBERS: tuple[FourNoksNumberDescription, ...] = (
    FourNoksNumberDescription(
        key="transmission_time",
        translation_key="transmission_time",
        native_min_value=1,
        native_max_value=65535,
        native_step=1,
        mode=NumberMode.BOX,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda d: getattr(
            getattr(d, "settings", None), "transmission_time", None
        ),
        set_value_fn=lambda d, v: d.settings.write("transmission_time", int(v)),
    ),
    FourNoksNumberDescription(
        key="standby_killer_time_window",
        translation_key="standby_killer_time_window",
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        mode=NumberMode.BOX,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda d: getattr(
            getattr(d, "settings", None), "standby_killer_time_window", None
        ),
        set_value_fn=lambda d, v: d.settings.write(
            "standby_killer_time_window", int(v)
        ),
    ),
    FourNoksNumberDescription(
        key="standby_killer_power_threshold",
        translation_key="standby_killer_power_threshold",
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        mode=NumberMode.BOX,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda d: getattr(
            getattr(d, "settings", None), "standby_killer_power_threshold", None
        ),
        set_value_fn=lambda d, v: d.settings.write(
            "standby_killer_power_threshold", int(v)
        ),
    ),
)

GATEWAY_NUMBERS: tuple[FourNoksNumberDescription, ...] = (
    FourNoksNumberDescription(
        key="route_regeneration_period",
        translation_key="route_regeneration_period",
        native_min_value=1,
        native_max_value=65535,
        native_step=1,
        mode=NumberMode.BOX,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda d: getattr(
            getattr(d, "settings", None), "route_regeneration_period", None
        ),
        set_value_fn=lambda d, v: d.settings.write("route_regeneration_period", int(v)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourNoksConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up 4-noks numbers."""
    coordinator = entry.runtime_data
    descriptions: tuple[FourNoksNumberDescription, ...] = ()

    if isinstance(coordinator.device, FourNoksPlug):
        descriptions = PLUG_NUMBERS
    elif isinstance(coordinator.device, FourNoksGateway):
        descriptions = GATEWAY_NUMBERS

    async_add_entities(FourNoksNumber(coordinator, desc) for desc in descriptions)


class FourNoksNumber(FourNoksEntity, NumberEntity):
    """Representation of a 4-noks number configuration entity."""

    entity_description: FourNoksNumberDescription

    def __init__(
        self,
        coordinator: FourNoksCoordinator,
        description: FourNoksNumberDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return native value."""
        val = self.entity_description.value_fn(self.coordinator.device)
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set native value."""
        await self.entity_description.set_value_fn(self.coordinator.device, value)
        await self.coordinator.async_request_refresh()
