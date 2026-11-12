# 4-noks Modbus Custom Integration for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/tomvanswam/four-noks-custom-component.svg)](https://github.com/tomvanswam/four-noks-custom-component/releases)
[![HACS Default](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License](https://img.shields.io/github/license/tomvanswam/four-noks-custom-component.svg)](LICENSE)

Custom integration for Home Assistant to control and monitor **4-noks ZB-Connection** Modbus devices (**ZC-GW-ETH-EM** Gateway and **ZR-PLUG-EU-M** / **ZR-PLUG-M** Smart Plugs).

## Supported Devices

- **ZR-PLUG-EU-M / ZR-PLUG-M**: Smart Plug socket relay switch, real-time power (W), cumulative energy (kWh), duration of operation, and wireless signal strength (dB).
- **ZC-GW-ETH-EM**: Ethernet / Zigbee Gateway RF diagnostics, network channel, PAN ID, connected node count, and mesh status.

## Installation via HACS

1. Make sure you have [HACS](https://hacs.xyz/) installed.
2. Open HACS in Home Assistant, click the three dots in the top right corner, and select **Custom repositories**.
3. Add `https://github.com/tomvanswam/four-noks-custom-component` with category **Integration**.
4. Search for `4-noks` in HACS and click **Download**.
5. Restart Home Assistant.

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
