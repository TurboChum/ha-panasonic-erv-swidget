# Panasonic ERV Home Assistant Integration

A custom Home Assistant integration for Panasonic ERV (Energy Recovery Ventilator) devices using the Swidget local API. Installable via HACS as a custom repository. All communication is local — no cloud, no authentication required.

## Features

### Controls
- **Power** — turn the ERV on or off
- **Mode** — ventilation mode: Heat Exchange, Supply, Exhaust, Recirculation
- **Speed** — fan speed: Low or High
- **Boost** — high-flow override mode (~1 hour hardware timer)
- **Auto Runtime** — enable/disable the device's built-in auto-runtime scheduler *(disabled by default)*
- **Intermittent Mode** — switch between continuous and duty-cycle ventilation *(disabled by default)*

> Boost, Speed, and Mode controls are automatically unavailable when the device is powered off, preventing commands that would inadvertently turn it back on.

### Sensors
- Indoor and outdoor temperature and humidity
- Supply and exhaust CFM (airflow)
- Power: current draw, rolling average, and average while running
- Duty Cycle (minutes)
- Device status and error state
- Filter cleaning and replacement alerts

### CFM mismatch alerts
Binary sensors that fire when measured CFM deviates from the configured target for the current speed mode. Configurable threshold and duration — suppressed automatically during defrost, recirc, or any state where airflow is intentionally stopped.

### Device config entities *(all disabled by default)*
Number entities for CFM limits (per speed tier, supply and exhaust), runtime, default timer, humidity/temperature thresholds, balancing offset, and log rate. CFM limits enforce a minimum 10 CFM gap between speed tiers. Enable only the ones relevant to your setup.

### Reliability
- Configurable poll interval, read/write retry count, and command verification delay
- Desired-state recovery: if boost or speed drifts from what HA last set (e.g. boost expires after ~1 hour, or a power cycle resets speed), the integration automatically resends the command

## Requirements

- Home Assistant 2024.1.0 or newer
- Panasonic ERV with a Swidget module on your local network
- The device's local IP address

## Installation

1. In HACS, go to **Integrations → ⋮ → Custom repositories**
2. Add this repository URL and set the type to **Integration**
3. Install **Panasonic ERV**
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration** and search for **Panasonic ERV**
6. Enter a device name and the local URL or IP of the ERV (e.g. `http://192.168.1.100`)

## Configuration

All settings are available after setup via **Settings → Devices & Services → Panasonic ERV → Configure**:

| Option | Default | Description |
|---|---|---|
| Poll Interval | 60 s | How often to fetch device state |
| Retry Count | 3 | Read/write retries before reporting an error |
| Verify Delay | 2 s | Seconds to wait after a command before re-polling to confirm |
| Auto-recover Desired State | On | Resend boost/speed commands if device state drifts |
| CFM Alert Threshold | 10 CFM | Deviation from target before the mismatch timer starts |
| CFM Alert Duration | 60 s | How long the deviation must persist before the sensor fires |

## Notes

- Tested against the Swidget-based Panasonic ERV (model `pesna_IB150`)
- CFM sensors report `-1` when the unit is off or in a non-airflow state (recirc, exhaust-only), keeping graphs continuous rather than creating data gaps
