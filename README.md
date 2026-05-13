# Panasonic ERV Home Assistant Integration

A custom Home Assistant integration for Panasonic ERV devices using the Swidget local API. Installable via HACS as a custom repository.

## Features

- **Controls**: power switch, ventilation mode (Heat Exchange / Supply / Exhaust / Recirculation), fan speed (Low / High), boost mode
- **Sensors**: status, indoor/outdoor temperature and humidity, supply/exhaust CFM, power usage, filter cleaning/replacement alerts
- **CFM mismatch alerts**: binary sensors that fire when measured CFM deviates from the configured target for the device's current speed — configurable threshold and duration
- **Device config entities**: number entities for CFM limits, runtime, humidity/temperature thresholds, and log rate (disabled by default; enable the ones you need)
- **Balancing**: select entity to enable/disable automatic supply/exhaust balancing
- **Polling with retry**: configurable poll interval, read/write retry count, and command verification delay
- **Desired-state recovery**: if boost or speed drifts from what HA last set, the integration automatically resends the command

## Installation

1. In HACS, add this repository as a custom integration repository
2. Install "Panasonic ERV"
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration** and search for "Panasonic ERV"
5. Enter a device name and the local URL or IP address of the ERV (e.g. `http://192.168.1.100`)

## Configuration

All settings are available after setup via **Settings → Devices & Services → Panasonic ERV → Configure**:

| Option | Default | Description |
|---|---|---|
| Poll Interval | 60 s | How often to fetch device state |
| Retry Count | 3 | Read/write retries before reporting an error |
| Verify Delay | 2 s | Seconds to wait after a command before re-polling to confirm |
| Auto-recover Desired State | On | Resend boost/speed commands if the device state drifts |
| CFM Alert Threshold | 10 CFM | Deviation from target before the mismatch timer starts |
| CFM Alert Duration | 60 s | How long the deviation must persist before the sensor fires |

## Device config number entities

The entities for CFM limits, runtime, thresholds, etc. are **disabled by default**. Enable only the ones relevant to your setup via the entity's settings in HA. These map directly to fields in `/api/v1/device_config`.

## Notes

- No authentication required — the integration communicates directly with the device on your local network
- Tested against the Swidget-based Panasonic ERV (model `pesna_IB150`)
- This repository is intended to remain private until the integration is ready for public release
