"""Common test utilities for Home Assistant integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import pathlib
import tempfile
from typing import Any
from unittest.mock import patch

from homeassistant import auth, bootstrap, config_entries, loader
from homeassistant.auth import auth_store
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlowResult,
)
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers import (
    area_registry as ar,
    category_registry as cr,
    condition,
    device_registry as dr,
    entity,
    entity_registry as er,
    floor_registry as fr,
    issue_registry as ir,
    label_registry as lr,
    restore_state as rs,
    storage,
    translation,
    trigger,
)
from homeassistant.util import dt as dt_util, ulid as ulid_util
from homeassistant.util.unit_system import METRIC_SYSTEM


class StoreWithoutWriteLoad(storage.Store):
    """Fake store that does not write or load. Used for testing."""

    async def async_save(self, *args: Any, **kwargs: Any) -> None:
        """Save the data."""

    @callback
    def async_save_delay(self, *args: Any, **kwargs: Any) -> None:
        """Save data with an optional delay."""


def ensure_auth_manager_loaded(auth_mgr: auth.AuthManager) -> None:
    """Ensure an auth manager is considered loaded."""
    store = auth_mgr._store
    if store._users is None:
        store._set_defaults()


class MockConfigEntry(ConfigEntry):
    """Helper for creating config entries in tests."""

    def __init__(
        self,
        *,
        data: dict[str, Any] | None = None,
        disabled_by: Any = None,
        discovery_keys: dict[str, Any] | None = None,
        domain: str = "test",
        entry_id: str | None = None,
        minor_version: int = 1,
        options: dict[str, Any] | None = None,
        pref_disable_new_entities: bool | None = None,
        pref_disable_polling: bool | None = None,
        reason: str | None = None,
        source: str = config_entries.SOURCE_USER,
        state: ConfigEntryState | None = None,
        subentries_data: Any = None,
        title: str = "Mock Title",
        unique_id: str | None = None,
        version: int = 1,
    ) -> None:
        """Initialize a mock config entry."""
        kwargs: dict[str, Any] = {
            "data": data or {},
            "disabled_by": disabled_by,
            "discovery_keys": discovery_keys or {},
            "domain": domain,
            "entry_id": entry_id or ulid_util.ulid_now(),
            "minor_version": minor_version,
            "options": options or {},
            "pref_disable_new_entities": pref_disable_new_entities,
            "pref_disable_polling": pref_disable_polling,
            "subentries_data": subentries_data or (),
            "title": title,
            "unique_id": unique_id,
            "version": version,
        }
        if source is not None:
            kwargs["source"] = source
        if state is not None:
            kwargs["state"] = state
        super().__init__(**kwargs)
        if reason is not None:
            object.__setattr__(self, "reason", reason)

    def add_to_hass(self, hass: HomeAssistant) -> None:
        """Add entry to hass config entries."""
        hass.config_entries._entries[self.entry_id] = self

    def add_to_manager(self, manager: config_entries.ConfigEntries) -> None:
        """Add entry to manager."""
        manager._entries[self.entry_id] = self

    def mock_state(
        self,
        hass: HomeAssistant,
        state: ConfigEntryState,
        reason: str | None = None,
    ) -> None:
        """Mock the state of a config entry."""
        self._async_set_state(hass, state, reason)

    async def start_reconfigure_flow(
        self,
        hass: HomeAssistant,
    ) -> ConfigFlowResult:
        """Start a reconfiguration flow."""
        if self.entry_id not in hass.config_entries._entries:
            raise ValueError(
                "Config entry must be added to hass to start reconfiguration flow"
            )
        return await hass.config_entries.flow.async_init(
            self.domain,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": self.entry_id,
            },
        )


@asynccontextmanager
async def async_test_home_assistant(
    config_dir: str | None = None,
    initial_state: CoreState = CoreState.running,
) -> AsyncGenerator[HomeAssistant, None]:
    """Return a Home Assistant object pointing at test config dir."""
    temp_dir: tempfile.TemporaryDirectory | None = None
    if config_dir is None:
        temp_dir = tempfile.TemporaryDirectory()
        test_dir = temp_dir.name
    else:
        test_dir = config_dir

    hass = HomeAssistant(test_dir)
    store = auth_store.AuthStore(hass)
    hass.auth = auth.AuthManager(hass, store, {}, {})
    ensure_auth_manager_loaded(hass.auth)

    orig_tz = dt_util.get_default_time_zone()

    hass.data[loader.DATA_CUSTOM_COMPONENTS] = {}

    hass.config.location_name = "test home"
    hass.config.latitude = 52.3676
    hass.config.longitude = 4.9041
    hass.config.elevation = 0
    await hass.config.async_set_time_zone("UTC")
    hass.config.units = METRIC_SYSTEM
    hass.config.media_dirs = {"local": str(pathlib.Path(test_dir) / "media")}
    hass.config.skip_pip = True
    hass.config.skip_pip_packages = []

    hass.config_entries = config_entries.ConfigEntries(
        hass,
        {"_": "test"},
    )
    hass.config_entries._initialized.set()
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP,
        hass.config_entries._async_shutdown,
    )

    entity.async_setup(hass)
    loader.async_setup(hass)
    await condition.async_setup(hass)
    await trigger.async_setup(hass)

    if hasattr(translation, "TRANSLATION_FLATTEN_CACHE"):
        hass.data[translation.TRANSLATION_FLATTEN_CACHE] = (
            translation._TranslationCache(hass)
        )

    dr.async_setup(hass)

    with (
        patch.object(StoreWithoutWriteLoad, "async_load", return_value=None),
        patch(
            "homeassistant.helpers.area_registry.AreaRegistryStore",
            StoreWithoutWriteLoad,
        ),
        patch(
            "homeassistant.helpers.device_registry.DeviceRegistryStore",
            StoreWithoutWriteLoad,
        ),
        patch(
            "homeassistant.helpers.entity_registry.EntityRegistryStore",
            StoreWithoutWriteLoad,
        ),
        patch(
            "homeassistant.helpers.storage.Store",
            StoreWithoutWriteLoad,
        ),
        patch(
            "homeassistant.helpers.issue_registry.IssueRegistryStore",
            StoreWithoutWriteLoad,
        ),
        patch(
            "homeassistant.helpers.restore_state.RestoreStateData.async_setup_dump",
            return_value=None,
        ),
        patch(
            "homeassistant.helpers.restore_state.start.async_at_start",
        ),
    ):
        await ar.async_load(hass)
        await cr.async_load(hass)
        await dr.async_load(hass)
        await er.async_load(hass)
        if hasattr(fr, "async_load"):
            await fr.async_load(hass)
        if hasattr(ir, "async_load"):
            await ir.async_load(hass)
        if hasattr(lr, "async_load"):
            await lr.async_load(hass)
        if hasattr(rs, "async_load"):
            await rs.async_load(hass)

    hass.data[bootstrap.DATA_REGISTRIES_LOADED] = None
    hass.set_state(initial_state)

    try:
        yield hass
    finally:
        dt_util.set_default_time_zone(orig_tz)
        loaded_entries = [
            entry
            for entry in hass.config_entries.async_entries()
            if entry.state is ConfigEntryState.LOADED
        ]
        if loaded_entries:
            await asyncio.gather(
                *(
                    hass.config_entries.async_unload(entry.entry_id)
                    for entry in loaded_entries
                )
            )
        await hass.async_stop(force=True)
        if temp_dir is not None:
            temp_dir.cleanup()
