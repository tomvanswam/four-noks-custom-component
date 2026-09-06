"""Config flow for 4-noks integration."""

from typing import Any

from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
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
from modbus_connection import ModbusError, ModbusTcpParams
import voluptuous as vol

try:
    from four_noks_modbus import DeviceType, FourNoksGateway, async_probe_device
except ImportError:
    from .vendor.four_noks_modbus import (
        DeviceType,
        FourNoksGateway,
        async_probe_device,
    )

from .const import (
    CONF_UNIT_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
)

CONF_AUTO_DISCOVER = "auto_discover"
CONF_SELECTED_NODES = "selected_nodes"


async def _async_discover_active_nodes(
    hass: HomeAssistant, host: str, port: int, unit_id: int
) -> dict[int, str]:
    """Probe the gateway and discover active nodes on the Zigbee network."""
    params = ModbusTcpParams(host=host, port=port)
    discovered_nodes: dict[int, str] = {}

    try:
        async with async_get_temporary_unit(hass, params, unit_id) as unit:
            presence_bits = await unit.read_discrete_inputs(16, 112)
            validity_bits = await unit.read_discrete_inputs(128, 112)

            for idx in range(min(len(presence_bits), len(validity_bits))):
                if presence_bits[idx] and validity_bits[idx]:
                    node_unit = 16 + idx
                    try:
                        async with async_get_temporary_unit(
                            hass, params, node_unit
                        ) as node_unit_obj:
                            node_dev = await async_probe_device(node_unit_obj)
                            if node_dev.info.device_type_code == DeviceType.PLUG:
                                discovered_nodes[node_unit] = (
                                    f"4-noks Smart Plug (Unit {node_unit})"
                                )
                            elif node_dev.info.device_type_code == DeviceType.GATEWAY:
                                discovered_nodes[node_unit] = (
                                    f"4-noks Gateway (Unit {node_unit})"
                                )
                    except (HomeAssistantError, ModbusError, OSError, ValueError):
                        continue
    except (HomeAssistantError, ModbusError, OSError):
        pass

    return discovered_nodes


def _async_update_child_plugs(
    hass: HomeAssistant,
    gateway_entry_id: str,
    old_host: str,
    old_port: int,
    new_host: str,
    new_port: int,
) -> None:
    """Update host and port for all child plugs belonging to a gateway."""
    for child_entry in hass.config_entries.async_entries(DOMAIN):
        if (
            child_entry.entry_id != gateway_entry_id
            and child_entry.data.get(CONF_HOST) == old_host
            and int(child_entry.data.get(CONF_PORT, 502)) == old_port
            and int(child_entry.data.get(CONF_UNIT_ID, 1)) > 1
        ):
            c_unit = int(child_entry.data[CONF_UNIT_ID])
            c_data = {
                **child_entry.data,
                CONF_HOST: new_host,
                CONF_PORT: new_port,
            }
            c_unique_id = f"{new_host}:{new_port}:{c_unit}"
            hass.config_entries.async_update_entry(
                child_entry,
                data=c_data,
                unique_id=c_unique_id,
            )
            hass.config_entries.async_schedule_reload(child_entry.entry_id)


class FourNoksConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 4-noks."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        self._host: str | None = None
        self._port: int = 502
        self._discovered_nodes: dict[int, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input[CONF_PORT])
            unit_id = int(user_input[CONF_UNIT_ID])
            self._host = host
            self._port = port

            await self.async_set_unique_id(f"{host}:{port}:{unit_id}")
            self._abort_if_unique_id_configured()

            params = ModbusTcpParams(host=host, port=port)
            try:
                async with async_get_temporary_unit(self.hass, params, unit_id) as unit:
                    device = await async_probe_device(unit)
            except (HomeAssistantError, ModbusError, OSError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                if (
                    user_input.get(CONF_AUTO_DISCOVER, True)
                    and unit_id == 1
                    and isinstance(device, FourNoksGateway)
                ):
                    return await self._async_handle_gateway_discovery(unit_id, device)
                return await self._async_create_device_entry(
                    host, port, unit_id, device.info.model
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
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _async_handle_gateway_discovery(
        self, unit_id: int, gateway_dev: FourNoksGateway
    ) -> ConfigFlowResult:
        """Probe the gateway and discover active nodes on the Zigbee network."""
        assert self._host is not None
        self._discovered_nodes = {unit_id: f"{gateway_dev.info.model} (Unit {unit_id})"}
        discovered = await _async_discover_active_nodes(
            self.hass, self._host, self._port, unit_id
        )
        self._discovered_nodes.update(discovered)

        if len(self._discovered_nodes) > 1:
            return await self.async_step_discover_nodes()

        return await self._async_create_device_entry(
            self._host, self._port, unit_id, gateway_dev.info.model
        )

    async def async_step_discover_nodes(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show discovered devices checklist to the user."""
        assert self._host is not None
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
                                CONF_HOST: self._host,
                                CONF_PORT: self._port,
                                CONF_UNIT_ID: u,
                            },
                        )
                    )
                return await self._async_create_device_entry(
                    self._host, self._port, primary_unit
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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of a 4-noks config entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        old_host = str(entry.data.get(CONF_HOST, "192.168.2.3")).strip()
        old_port = int(entry.data.get(CONF_PORT, 502))
        old_unit_id = int(entry.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID))

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input[CONF_PORT])
            unit_id = int(user_input[CONF_UNIT_ID])

            new_unique_id = f"{host}:{port}:{unit_id}"
            await self.async_set_unique_id(new_unique_id)
            self._abort_if_unique_id_configured()

            params = ModbusTcpParams(host=host, port=port)
            try:
                async with async_get_temporary_unit(self.hass, params, unit_id) as unit:
                    device = await async_probe_device(unit)
            except (HomeAssistantError, ModbusError, OSError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                if (host != old_host or port != old_port) and old_unit_id == 1:
                    _async_update_child_plugs(
                        self.hass,
                        entry.entry_id,
                        old_host,
                        old_port,
                        host,
                        port,
                    )

                model = getattr(device.info, "model", None)
                title = f"{model} ({unit_id})" if model else entry.title
                return self.async_update_reload_and_abort(
                    entry,
                    title=title,
                    data={
                        **entry.data,
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_UNIT_ID: unit_id,
                    },
                    unique_id=new_unique_id,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=old_host): TextSelector(),
                vol.Required(CONF_PORT, default=old_port): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=65535, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(CONF_UNIT_ID, default=old_unit_id): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=247, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_discovery(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Handle background entry creation for discovered devices."""
        host = data[CONF_HOST]
        port = int(data[CONF_PORT])
        unit_id = int(data[CONF_UNIT_ID])
        await self.async_set_unique_id(f"{host}:{port}:{unit_id}")
        self._abort_if_unique_id_configured()

        params = ModbusTcpParams(host=host, port=port)
        title = None
        try:
            async with async_get_temporary_unit(self.hass, params, unit_id) as unit:
                device = await async_probe_device(unit)
                title = f"{device.info.model} ({unit_id})"
        except (HomeAssistantError, ModbusError, OSError, ValueError):
            pass

        title = title or f"4-noks ({unit_id})"
        return self.async_create_entry(title=title, data=data)

    async def _async_create_device_entry(
        self,
        host: str,
        port: int,
        unit_id: int,
        model_name: str | None = None,
    ) -> ConfigFlowResult:
        """Create an entry for a single device."""
        data = {CONF_HOST: host, CONF_PORT: port, CONF_UNIT_ID: unit_id}
        await self.async_set_unique_id(f"{host}:{port}:{unit_id}")
        self._abort_if_unique_id_configured()

        if model_name is None:
            params = ModbusTcpParams(host=host, port=port)
            try:
                async with async_get_temporary_unit(self.hass, params, unit_id) as unit:
                    device = await async_probe_device(unit)
                    model_name = device.info.model
            except (HomeAssistantError, ModbusError, OSError, ValueError):
                pass

        title = f"{model_name} ({unit_id})" if model_name else f"4-noks ({unit_id})"
        return self.async_create_entry(title=title, data=data)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Get the options flow for this handler."""
        return FourNoksOptionsFlow()


class FourNoksOptionsFlow(OptionsFlow):
    """Handle options flow for a 4-noks device."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._host: str | None = None
        self._port: int = 502
        self._scan_interval: int = DEFAULT_SCAN_INTERVAL
        self._discovered_nodes: dict[int, str] = {}

    def _is_gateway(self) -> bool:
        """Check if current entry is a gateway."""
        unit_id = int(self.config_entry.data.get(CONF_UNIT_ID, 1))
        if unit_id == 1:
            return True
        if self.config_entry.runtime_data is not None:
            device = getattr(self.config_entry.runtime_data, "device", None)
            if isinstance(device, FourNoksGateway):
                return True
        return False

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage 4-noks device options."""
        if not self._is_gateway():
            if user_input is not None:
                return self.async_create_entry(title="", data=user_input)

            current_interval = self.config_entry.options.get(
                CONF_SCAN_INTERVAL,
                self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=5,
                            max=3600,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                }
            )
            return self.async_show_form(step_id="init", data_schema=schema)

        # Gateway device options
        errors: dict[str, str] = {}
        old_host = str(self.config_entry.data.get(CONF_HOST, "192.168.2.3")).strip()
        old_port = int(self.config_entry.data.get(CONF_PORT, 502))
        old_unit_id = int(self.config_entry.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID))
        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input[CONF_PORT])
            unit_id = int(user_input[CONF_UNIT_ID])
            scan_interval = int(user_input[CONF_SCAN_INTERVAL])
            auto_discover = bool(user_input.get(CONF_AUTO_DISCOVER, False))

            connection_changed = (
                host != old_host or port != old_port or unit_id != old_unit_id
            )
            new_unique_id = f"{host}:{port}:{unit_id}"

            if connection_changed:
                for entry in self.hass.config_entries.async_entries(DOMAIN):
                    if entry.entry_id != self.config_entry.entry_id and (
                        entry.unique_id == new_unique_id
                        or (
                            entry.data.get(CONF_HOST) == host
                            and int(entry.data.get(CONF_PORT, 502)) == port
                            and int(entry.data.get(CONF_UNIT_ID, 1)) == unit_id
                        )
                    ):
                        errors["base"] = "already_configured"
                        break

            device = None
            if not errors and (connection_changed or auto_discover):
                params = ModbusTcpParams(host=host, port=port)
                try:
                    async with async_get_temporary_unit(
                        self.hass, params, unit_id
                    ) as unit:
                        device = await async_probe_device(unit)
                except (HomeAssistantError, ModbusError, OSError, ValueError):
                    errors["base"] = "cannot_connect"

            if not errors:
                if connection_changed:
                    model = getattr(device.info, "model", None) if device else None
                    title = f"{model} ({unit_id})" if model else self.config_entry.title
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        title=title,
                        data={
                            **self.config_entry.data,
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_UNIT_ID: unit_id,
                        },
                        unique_id=new_unique_id,
                    )
                    if host != old_host or port != old_port:
                        _async_update_child_plugs(
                            self.hass,
                            self.config_entry.entry_id,
                            old_host,
                            old_port,
                            host,
                            port,
                        )

                if auto_discover:
                    self._host = host
                    self._port = port
                    self._scan_interval = scan_interval

                    configured_units = {
                        int(entry.data.get(CONF_UNIT_ID, 1))
                        for entry in self.hass.config_entries.async_entries(DOMAIN)
                        if entry.data.get(CONF_HOST) == host
                        and int(entry.data.get(CONF_PORT, 502)) == port
                    }
                    discovered = await _async_discover_active_nodes(
                        self.hass, host, port, unit_id
                    )
                    self._discovered_nodes = {
                        u: name
                        for u, name in discovered.items()
                        if u not in configured_units
                    }

                    if self._discovered_nodes:
                        return await self.async_step_discover_nodes()

                return self.async_create_entry(
                    title="", data={CONF_SCAN_INTERVAL: scan_interval}
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=old_host): TextSelector(),
                vol.Required(CONF_PORT, default=old_port): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=65535, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(CONF_UNIT_ID, default=old_unit_id): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=247, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current_interval
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5,
                        max=3600,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Required(CONF_AUTO_DISCOVER, default=False): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    async def async_step_discover_nodes(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show discovered devices checklist to the user."""
        assert self._host is not None
        if user_input is not None:
            selected = [int(x) for x in user_input.get(CONF_SELECTED_NODES, [])]
            for u in selected:
                self.hass.async_create_task(
                    self.hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={"source": "discovery"},
                        data={
                            CONF_HOST: self._host,
                            CONF_PORT: self._port,
                            CONF_UNIT_ID: u,
                        },
                    )
                )
            return self.async_create_entry(
                title="", data={CONF_SCAN_INTERVAL: self._scan_interval}
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
