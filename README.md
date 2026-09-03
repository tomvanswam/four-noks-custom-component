# 4-noks Modbus Custom Integration for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/tomvanswam/four-noks-custom-component.svg)](https://github.com/tomvanswam/four-noks-custom-component/releases)
[![HACS Default](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License](https://img.shields.io/github/license/tomvanswam/four-noks-custom-component.svg)](LICENSE)

Custom integration for Home Assistant to control and monitor **4-noks ZB-Connection** Modbus devices (**ZC-GW-ETH-EM** Gateway and **ZR-PLUG-EU-M** / **ZR-PLUG-M** Smart Plugs).

> [!NOTE]
> This custom component contains a vendorized copy of the `four_noks_modbus` device library, allowing it to be tested immediately via HACS without waiting for upstream package releases.
> It uses Home Assistant's new `modbus_connection` hub architecture.

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

1. Make sure you have configured a **Modbus Connection** entry under **Settings -> Devices & Services -> Add Integration -> Modbus Connection** (TCP or Serial).
2. Go to **Settings -> Devices & Services -> Add Integration**.
3. Search for **4-noks**.
4. Select your configured Modbus Connection and enter the device unit ID:
   - Default for Gateway: `1`
   - Default for Smart Plugs: `16` to `126` (e.g. `102`)
5. The integration will automatically probe the device, detect whether it is a Smart Plug or Gateway, and set up all entities.
