# 4-noks Modbus Custom Integration for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/tomvanswam/four-noks-custom-component.svg)](https://github.com/tomvanswam/four-noks-custom-component/releases)
[![Marketplace](https://img.shields.io/badge/Marketplace-Custom%20repository-orange.svg)](https://www.home-assistant.io/blog/2026/11/04/release-202611/)
[![License](https://img.shields.io/github/license/tomvanswam/four-noks-custom-component.svg)](LICENSE)

Custom integration for Home Assistant to control and monitor **4-noks ZB-Connection** Modbus devices (**ZC-GW-ETH-EM** Gateway and **ZR-PLUG-EU-M** / **ZR-PLUG-M** Smart Plugs).

## Supported Devices

- **ZR-PLUG-EU-M / ZR-PLUG-M**: Smart Plug socket relay switch, real-time power (W), cumulative energy (kWh), duration of operation, and wireless signal strength (dB).
- **ZC-GW-ETH-EM**: Ethernet / Zigbee Gateway RF diagnostics, network channel, PAN ID, connected node count, and mesh status.

## Requirements

- Home Assistant **2026.9.0** or newer. Older versions are refused at setup (and by the Marketplace/HACS).

## Installation via the Marketplace

Since Home Assistant 2026.11, HACS is built in as the **Marketplace**. This integration is not (yet) in the community catalog, so add it as a custom repository:

1. Go to **Settings -> Marketplace** (you need to be an administrator).
2. Select **Add from link** and enter `https://github.com/tomvanswam/four-noks-custom-component`. Custom repositories require connecting the Marketplace to GitHub; follow the GitHub sign-in prompt if asked.
3. Open **4-noks** from the list, select **Install** and confirm the warning.
4. The integration loads without a restart and you go straight to its setup flow (see [Configuration](#configuration)). Updates later on still require a restart.

### Home Assistant 2026.9 or 2026.10 (HACS)

On versions before 2026.11, install it with [HACS](https://hacs.xyz/):

1. Open HACS, click the three dots in the top right corner, and select **Custom repositories**.
2. Add `https://github.com/tomvanswam/four-noks-custom-component` with category **Integration**.
3. Search for `4-noks` in HACS and click **Download**.
4. Restart Home Assistant.

When you upgrade to 2026.11 or newer, HACS is replaced by the Marketplace (see the [2026.11 release notes](https://www.home-assistant.io/blog/2026/11/04/release-202611/)).

## Configuration

The integration connects directly over **Modbus TCP**; no separate Modbus integration entry is needed.

1. Go to **Settings -> Devices & Services -> Add Integration** and search for **4-noks**.
2. Fill in the form:

   | Field | Description | Default |
   |---|---|---|
   | **Host** | IP address or hostname of the 4-noks gateway (ZC-GW-ETH-EM) | `192.168.2.3` |
   | **Port** | Modbus TCP port | `502` |
   | **Unit ID** | Modbus unit ID: gateway `1`, smart plugs `16` to `126` (e.g. `102`) | `1` |
   | **Auto discover** | Only applies when Unit ID is `1` (gateway), see below | on |

3. The integration probes the device and detects whether it is a gateway or a smart plug. If it cannot connect, the form shows *Failed to connect*.
4. With **Auto discover** enabled on the gateway (unit `1`), the gateway's Zigbee network is scanned for active nodes (units `16` to `126`). Select the plugs (and gateway) you want to add; a separate config entry is created for each selected unit. Without auto discover, only the unit you entered is added; add plugs later by repeating these steps with their unit ID.

### Changing settings later

- **Reconfigure** (entry menu -> *Reconfigure*): change host, port or unit ID. When the host/port of a gateway changes, the plugs behind it are updated automatically.
- **Configure** (options): change the polling interval (seconds). On a gateway you can also adjust host, port and unit ID and run auto discover again to add newly paired plugs.

### Upgrading from an earlier version

Earlier versions required a separate **Modbus Connection** entry that the 4-noks entries referred to. Existing 4-noks entries are migrated automatically on first start: host and port are copied from the referenced Modbus Connection entry into the 4-noks entry. After the 4-noks devices are loaded again, the old Modbus Connection entry is no longer used and can be removed.
