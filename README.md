# Panasonic ERV Home Assistant Integration

A custom Home Assistant integration for Panasonic ERV (Energy Recovery Ventilator) devices using the Swidget local API. Installable via HACS as a custom repository. All communication is local — no cloud, no authentication required.

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

---

## Entities

### Switches

**Power**
Turns the ERV on or off. Always available.

**Boost**
Activates the device's high-flow override mode. The device hardware enforces a ~1 hour timer — boost turns itself off automatically. Unavailable when the device is powered off (to prevent inadvertently turning it back on). If desired-state recovery is enabled, the integration will resend the boost command if it detects boost has expired before you turned it off in HA.

**Auto Runtime** *(disabled by default)*
Enables the device's built-in auto-runtime scheduler. When active, the device automatically manages the intermittent on/off interval based on outdoor temperature conditions. Works in conjunction with the Intermittent Mode switch. When the device is in its auto-managed off period, the Status sensor will read `auto`.

**Intermittent Mode** *(disabled by default)*
Switches the ERV between continuous operation and duty-cycle (intermittent) ventilation. When enabled, the device runs for the duration set by the **Runtime** number entity, then pauses, and repeats. When the device is in its configured off period, the Status sensor will read `int`.

---

### Selects

**Mode**
Sets the ventilation mode. Unavailable when the device is powered off.

| Value | Description |
|---|---|
| `Heat Exchange` | Exchanges heat between supply and exhaust air (normal ERV operation) |
| `Supply` | Supply air only |
| `Exhaust` | Exhaust air only |
| `Recirculation` | Recirculates indoor air without exchanging with outside |

**Speed**
Sets the fan speed. Unavailable when the device is powered off. If desired-state recovery is enabled, the integration will resend the speed command if the device drifts (e.g. after a power cycle).

| Value | Description |
|---|---|
| `Low` | Low fan speed |
| `High` | High fan speed |

**Balancing** *(disabled by default)*
Controls whether supply/exhaust airflow balance is set manually (via the CFM number entities) or managed automatically by the device.

| Value | Description |
|---|---|
| `Manual` | CFM targets are set by the user via the CFM number entities |
| `Auto` | Device manages supply/exhaust balance automatically |

---

### Sensors

**Indoor Temperature**
Current indoor temperature in °C as measured by the ERV. Shows **Unknown** when the device is idle and the sensor has no valid reading (the device reports 53°C / 127.4°F as a sentinel in this state).

**Outdoor Temperature**
Current outdoor temperature in °C as measured by the ERV. Shows **Unknown** under the same idle conditions as Indoor Temperature.

**Indoor Humidity**
Current indoor relative humidity (%).

**Outdoor Humidity**
Current outdoor relative humidity (%).

**Supply CFM**
Measured supply airflow in CFM. Reports `-1` when the unit is off or in a non-airflow state (recirc, exhaust-only, etc.) — this keeps graphs continuous rather than creating data gaps.

**Exhaust CFM**
Measured exhaust airflow in CFM. Reports `-1` under the same conditions as Supply CFM.

**Power**
Current power draw in watts.

**Average Power**
Rolling average power draw in watts (includes time when the unit is off).

**Average Power While On**
Average power draw in watts, calculated only while the unit is running.

**Status**
Current operating status of the device. Reports one of:

| Value | Meaning |
|---|---|
| `normal` | Running normally |
| `boost` | Boost mode active |
| `int` | Off — currently in the configured-off period of an intermittent runtime cycle |
| `auto` | Off — currently in the off period of the auto runtime cycle (outdoor temp-based scheduling) |

**Error**
Current error code or state reported by the device.

---

### Binary Sensors (Alerts)

**Filter Needs Cleaning**
Fires when the device reports the filter requires cleaning.

**Filter Needs Replacement**
Fires when the device reports the filter requires replacement.

**Supply CFM Mismatch**
Fires when the measured supply CFM deviates from the configured target for the current speed mode by more than the configured threshold, and that deviation has persisted for longer than the configured duration. Automatically suppressed when the device is off, in recirculation mode, or during defrost — any state where airflow is intentionally stopped. Exposes `target_cfm`, `actual_cfm`, `speed_mode`, and `mismatch_since` as attributes.

**Exhaust CFM Mismatch**
Same as Supply CFM Mismatch but for the exhaust side.

---

### Number Entities — Device Config *(all disabled by default)*

These entities expose numeric settings stored on the device. Enable only the ones relevant to your setup. All writes are confirmed by re-polling the device after the configured verify delay.

#### CFM Limits

Six entities set the target CFM for each speed tier (Low, High, Boost) on each side (Supply, Exhaust). The device reports its physical airflow ceiling, and the integration uses that as the absolute maximum for Boost. A minimum 10 CFM gap is enforced between adjacent tiers — you cannot set Low higher than High minus 10, or High higher than Boost minus 10.

| Entity | Description | Min | Max |
|---|---|---|---|
| Low Speed Supply CFM | Supply CFM target at Low speed | 30 | High Supply CFM − 10 |
| Low Speed Exhaust CFM | Exhaust CFM target at Low speed | 30 | High Exhaust CFM − 10 |
| High Speed Supply CFM | Supply CFM target at High speed | 30 | Boost Supply CFM − 10 |
| High Speed Exhaust CFM | Exhaust CFM target at High speed | 30 | Boost Exhaust CFM − 10 |
| Boost Supply CFM | Supply CFM target during Boost | 30 | Device physical ceiling |
| Boost Exhaust CFM | Exhaust CFM target during Boost | 30 | Device physical ceiling |

#### Timing

**Runtime** — Sets the on-duration for intermittent ventilation cycles, used when **Intermittent Mode** is enabled. Range: **15–60 minutes** (device-enforced limit).

**Default Timer** — Purpose and range not yet fully confirmed from device testing.

#### Humidity and Temperature Thresholds

**Humidity Control Setpoint** — Target humidity level for the humidity control feature. Range: 0–100%.

**High Humidity Threshold** — Humidity level above which the device may alter behavior. Range: 0–100%.

**Low Temperature Threshold** — Temperature below which the device may alter behavior (e.g. defrost). Range: −30 to 30°C.

#### Other

**Balancing Offset** — Adjusts the CFM balance between supply and exhaust by a fixed offset. Range: −10 to +10 CFM.

**Supply Limit Low Temp** — Flag (0 or 1). Exact behavior not yet confirmed from device testing.

**Supply Limit High Humidity** — Flag (0 or 1). Exact behavior not yet confirmed from device testing.

---

## Reliability

- **Retry logic** — all reads and writes are retried up to the configured retry count before reporting an error
- **Command verification** — after every write, the integration waits the configured verify delay then re-polls the device to confirm the change took effect
- **Desired-state recovery** — if boost or speed drifts from the last command HA sent (e.g. boost expires after ~1 hour, or a power cycle resets speed), the integration detects the mismatch on the next poll and automatically resends the command

## Notes

- Tested against the Swidget-based Panasonic ERV (model `pesna_IB150`)
- CFM sensors report `-1` when the unit is off or in a non-airflow state, keeping graphs continuous rather than creating data gaps
