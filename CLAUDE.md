# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (domain `four_noks`, distributed via HACS) for 4-noks ZB-Connection Modbus TCP devices: the **ZC-GW-ETH-EM** gateway (Modbus unit `1`) and **ZR-PLUG-M / ZR-PLUG-EU-M** smart plugs (units `16`–`126`, reached through the gateway's host/port). Minimum Home Assistant version is `2026.9.0` (in `hacs.json` and `MIN_HA_VERSION` in `__init__.py`; keep both in sync).

## Commands

```bash
scripts/setup                 # pip install dev + lint requirements
scripts/lint                  # ruff format --check . && ruff check .
ruff format . && ruff check --fix .
scripts/develop               # run a local HA (`hass`) from ./config with this component on PYTHONPATH
pytest                        # all tests (testpaths=tests, asyncio_mode=auto)
pytest tests/test_switch.py::test_name -v   # single test
```

Tests need a Home Assistant install that ships the native `modbus` component's `async_get_unit` / `async_get_temporary_unit` API and the `modbus_connection` package (incl. `modbus_connection.mock`). Released HA from PyPI may not have it; CI runs pytest inside the `ghcr.io/home-assistant/home-assistant:dev` container (only `pytest-asyncio` added). Locally, the easiest equivalent is:

```bash
docker run --rm -v "$PWD":/repo -w /repo ghcr.io/home-assistant/home-assistant:dev \
  sh -c "pip install -q pytest-asyncio && pytest tests/ -v"
```

CI (`.github/workflows/`) runs HACS action, hassfest, Ruff and pytest on every non-main push/PR. Ruff targets py312 and excludes `custom_components/four_noks/vendor/`.

## Architecture

- **Transport is Home Assistant's own `modbus` component** (manifest `dependencies: ["modbus"]`), not pymodbus directly. `__init__.py` gets a shared unit via `homeassistant.components.modbus.async_get_unit(hass, entry, ModbusTcpParams, unit_id)`; `config_flow.py` uses `async_get_temporary_unit(...)` as an async context manager for probing. When the connection drops, `unit.on_connection_lost` schedules a full entry reload.
- **Device library is vendored** at `custom_components/four_noks/vendor/four_noks_modbus/`. Every import uses `try: from four_noks_modbus import ... except ImportError: from .vendor.four_noks_modbus import ...`; follow that pattern for new imports. The library holds all register addresses and decoding: `async_probe_device(unit)` reads the device-type register (input register 0: `38` = plug, `112` = gateway) and returns `FourNoksPlug` (subsystems `measurements`, `switch`, `settings`) or `FourNoksGateway` (`radio`, `network`, `settings`). New Modbus datapoints belong in the vendor subsystems, not in the HA platforms.
- **One config entry per Modbus unit.** `unique_id` is `"{host}:{port}:{unit_id}"`. Gateway auto-discover in the config flow reads discrete inputs 16..127 (node presence) and 128..239 (data validity), probes each active node and creates a separate entry for each selected unit. Reconfigure of a gateway's host/port propagates to the plug entries behind it. `async_setup_entry` also migrates old entries that lack host/port/unit_id (legacy `connection` entry reference).
- **`FourNoksCoordinator`** (`coordinator.py`, `entry.runtime_data`, typed `FourNoksConfigEntry`) polls `device.async_update()` on the options/data `scan_interval` (default 30 s). Besides the device itself it reads node presence/validity from the gateway: for the gateway entry the whole table (`nodes_presence`, `nodes_data_valid`), for a plug entry its own bits from unit 1 (`gateway_node_presence`, `gateway_node_data_valid`).
- **Platforms** (`binary_sensor`, `button`, `number`, `sensor`, `switch`) are mostly entity-description driven (`switch` uses explicit classes): separate `PLUG_*` / `GATEWAY_*` tuples of frozen dataclasses with `value_fn(device)` lambdas, chosen by `isinstance` on `coordinator.device`. All entities subclass `FourNoksEntity` (`entity.py`): unique id `"{entry_id}_{key}"`, one HA device per config entry.
- **Translations**: entity names use `translation_key`. `strings.json` and `translations/en.json` are identical copies; edit both.

## Tests

`tests/common.py` is a local copy of Home Assistant's test helpers (`MockConfigEntry`, `async_test_home_assistant`); `pytest-homeassistant-custom-component` is not used. `tests/conftest.py` autouse-patches `async_get_unit` / `async_get_temporary_unit` (in this package and in `homeassistant.components.modbus`) to return units from an in-memory `MockModbusConnection`, seeded with plug (unit 102) and gateway (unit 1) register maps. When adding a datapoint, seed its register in those dicts. If a new module imports `async_get_unit` directly, add a matching patch target there.

## Releases and versioning

Do not bump `version` in `manifest.json` by hand. On every push to `main`, `release.yml` runs `scripts/release.py`, which parses **Conventional Commits** since the last `v*` tag: `feat` gives a minor bump, `fix`/other types a patch, `!` or `BREAKING CHANGE:` a major (0.x goes to 1.0.0); `ci`, `chore` and `docs` alone produce no release. It commits the new manifest version with `[skip ci]`, tags, and publishes `four_noks.zip` as a GitHub release. Use Conventional Commit messages accordingly. `tests/test_release_script.py` covers the script.
