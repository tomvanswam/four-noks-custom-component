"""Config flow for 4-noks integration."""

from typing import Any

try:
    from four_noks_modbus import FourNoksGateway, async_probe_device
except ImportError:
    from .vendor.four_noks_modbus import FourNoksGateway, async_probe_device

from modbus_connection import ModbusError
import voluptuous as vol

try:
    from homeassistant.components.modbus_connection import (
        ConnectionNotReady,
        async_get_unit,
    )
except ImportError:
    from custom_components.modbus_connection import (
        ConnectionNotReady,
        async_get_unit,
    )

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import CONF_CONNECTION, CONF_UNIT_ID, DEFAULT_UNIT_ID, DOMAIN

CONF_AUTO_DISCOVER = "auto_discover"
CONF_SELECTED_NODES = "selected_nodes"
NEW_CONNECTION_VALUE = "__new__"


class FourNoksConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 4-noks."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        self._connection_id: str | None = None
        self._discovered_nodes: dict[int, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial user step."""
        errors: dict[str, str] = {}
        connections = self.hass.config_entries.async_entries("modbus_connection")

        if not connections:
            # No existing connection: ask for Host, Port, and Unit ID directly
            if user_input is not None:
                conn_id = await self._async_create_or_get_connection(
                    user_input[CONF_HOST], int(user_input[CONF_PORT])
                )
                if not conn_id:
                    errors["base"] = "cannot_connect"
                else:
                    self._connection_id = conn_id
                    unit_id = int(user_input[CONF_UNIT_ID])
                    if user_input.get(CONF_AUTO_DISCOVER, True) and unit_id == 1:
                        return await self._async_handle_gateway_discovery(unit_id)
                    return await self._async_create_device_entry(
                        self._connection_id, unit_id
                    )

            schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default="192.168.2.3"): TextSelector(),
                    vol.Required(CONF_PORT, default=502): NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=65535, step=1, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=247, step=1, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(CONF_AUTO_DISCOVER, default=True): BooleanSelector(),
                }
            )
            return self.async_show_form(
                step_id="user", data_schema=schema, errors=errors
            )

        # Existing connection(s) present: let user pick or create a new one
        if user_input is not None:
            conn_choice = user_input[CONF_CONNECTION]
            if conn_choice == NEW_CONNECTION_VALUE:
                return await self.async_step_new_connection()

            self._connection_id = conn_choice
            unit_id = int(user_input[CONF_UNIT_ID])
            if user_input.get(CONF_AUTO_DISCOVER, True) and unit_id == 1:
                return await self._async_handle_gateway_discovery(unit_id)
            return await self._async_create_device_entry(self._connection_id, unit_id)

        options = []
        for entry in connections:
            host_str = entry.data.get(CONF_HOST, "Modbus")
            port_str = entry.data.get(CONF_PORT, "")
            label = entry.title or f"{host_str}:{port_str}"
            options.append(SelectOptionDict(value=entry.entry_id, label=label))
        options.append(
            SelectOptionDict(
                value=NEW_CONNECTION_VALUE, label="+ New Modbus Connection..."
            )
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CONNECTION, default=options[0]["value"]
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=options, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=247, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(CONF_AUTO_DISCOVER, default=True): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_new_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a new Modbus connection entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            conn_id = await self._async_create_or_get_connection(
                user_input[CONF_HOST], int(user_input[CONF_PORT])
            )
            if not conn_id:
                errors["base"] = "cannot_connect"
            else:
                self._connection_id = conn_id
                return await self._async_handle_gateway_discovery(1)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="192.168.2.3"): TextSelector(),
                vol.Required(CONF_PORT, default=502): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=65535, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="new_connection", data_schema=schema, errors=errors
        )

    async def _async_create_or_get_connection(self, host: str, port: int) -> str | None:
        """Create or find a matching modbus_connection entry."""
        for entry in self.hass.config_entries.async_entries("modbus_connection"):
            if entry.data.get(CONF_HOST) == host and entry.data.get(CONF_PORT) == port:
                return entry.entry_id

        # Create connection via modbus_connection config flow
        result = await self.hass.config_entries.flow.async_init(
            "modbus_connection",
            context={"source": "network"},
            data={"host": host, "port": port},
        )
        if result.get("type") == "create_entry":
            return result["result"].entry_id
        return None

    async def _async_handle_gateway_discovery(self, unit_id: int) -> ConfigFlowResult:
        """Probe the gateway and discover active nodes on the Zigbee network."""
        assert self._connection_id is not None
        try:
            unit = async_get_unit(self.hass, self._connection_id, unit_id)
            device = await async_probe_device(unit)
        except (ConnectionNotReady, ModbusError, OSError, ValueError):
            return await self._async_create_device_entry(self._connection_id, unit_id)

        if not isinstance(device, FourNoksGateway):
            return await self._async_create_device_entry(self._connection_id, unit_id)

        # Gateway detected! Read active nodes table (Discrete Inputs 16..127)
        self._discovered_nodes = {unit_id: f"{device.info.model} (Unit {unit_id})"}
        try:
            node_bits = await unit.read_discrete_inputs(16, 112)
            for idx, active in enumerate(node_bits):
                if active:
                    node_unit = 16 + idx
                    self._discovered_nodes[node_unit] = (
                        f"4-noks Smart Plug (Unit {node_unit})"
                    )
        except (ModbusError, OSError):
            pass

        if len(self._discovered_nodes) > 1:
            return await self.async_step_discover_nodes()

        return await self._async_create_device_entry(self._connection_id, unit_id)

    async def async_step_discover_nodes(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show discovered devices checklist to the user."""
        if user_input is not None:
            selected = [int(x) for x in user_input.get(CONF_SELECTED_NODES, [])]
            if selected:
                primary_unit = selected[0]
                extra_units = selected[1:]
                for u in extra_units:
                    self.hass.async_create_task(
                        self.hass.config_entries.flow.async_init(
                            DOMAIN,
                            context={"source": "discovery"},
                            data={
                                CONF_CONNECTION: self._connection_id,
                                CONF_UNIT_ID: u,
                            },
                        )
                    )
                return await self._async_create_device_entry(
                    self._connection_id, primary_unit
                )

        options = [
            SelectOptionDict(value=str(u), label=name)
            for u, name in self._discovered_nodes.items()
        ]
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SELECTED_NODES,
                    default=[str(u) for u in self._discovered_nodes],
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="discover_nodes", data_schema=schema)

    async def async_step_discovery(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Handle background entry creation for discovered devices."""
        conn_id = data[CONF_CONNECTION]
        unit_id = int(data[CONF_UNIT_ID])
        await self.async_set_unique_id(f"{conn_id}_{unit_id}")
        self._abort_if_unique_id_configured()
        title = await self._async_title(data) or f"4-noks ({unit_id})"
        return self.async_create_entry(title=title, data=data)

    async def _async_create_device_entry(
        self, connection_id: str, unit_id: int
    ) -> ConfigFlowResult:
        """Validate and create an entry for a single device."""
        data = {CONF_CONNECTION: connection_id, CONF_UNIT_ID: unit_id}
        await self.async_set_unique_id(f"{connection_id}_{unit_id}")
        self._abort_if_unique_id_configured()

        title = await self._async_title(data)
        if title is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                errors={"base": "cannot_connect"},
            )
        return self.async_create_entry(title=title, data=data)

    async def _async_title(self, data: dict[str, Any]) -> str | None:
        """Probe the device for the entry title, or return None if unreachable."""
        try:
            unit = async_get_unit(
                self.hass, data[CONF_CONNECTION], int(data[CONF_UNIT_ID])
            )
            device = await async_probe_device(unit)
        except (ConnectionNotReady, ModbusError, OSError, ValueError):
            return None
        return f"{device.info.model} ({int(data[CONF_UNIT_ID])})"
