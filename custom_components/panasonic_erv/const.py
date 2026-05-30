"""Constants for the Panasonic ERV integration.

All string keys and default values live here so they can be imported by any
module without creating circular imports.  Nothing in this file has logic —
it is purely a shared dictionary of names and numbers.
"""

# The domain is the unique identifier HA uses for this integration.
# It must match the "domain" field in manifest.json.
DOMAIN = "panasonic_erv"

DEFAULT_NAME = "Panasonic ERV"

# --- Polling / reliability defaults ---
# These are the values used when the user has not yet opened the options flow.
DEFAULT_POLL_INTERVAL = 60    # seconds between state refreshes
DEFAULT_RETRY_COUNT = 3       # attempts before giving up on a read or write
DEFAULT_VERIFY_DELAY = 2      # seconds to wait after a command before re-polling
DEFAULT_BOOST_RECOVERY = True # auto-resend boost/speed if the device drifts

# --- Config entry data keys (stored permanently in the entry) ---
# These are set once during the setup wizard and do not change unless the
# integration is removed and re-added.
CONF_DEVICE_URL = "device_url"
CONF_DEVICE_NAME = "device_name"
CONF_MAC = "mac"              # used as the stable device identifier in the device registry
CONF_FW_VERSION = "fw_version"
CONF_MODEL_NAME = "model_name"

# --- Options keys (user-adjustable after setup) ---
CONF_POLL_INTERVAL = "poll_interval"
CONF_RETRY_COUNT = "retry_count"
CONF_VERIFY_DELAY = "verify_delay"
CONF_BOOST_RECOVERY = "boost_recovery"
CONF_CFM_ALERT_THRESHOLD = "cfm_alert_threshold"  # CFM delta that starts the mismatch timer
CONF_CFM_ALERT_DURATION = "cfm_alert_duration"    # seconds the delta must persist before alerting

# --- CFM alert defaults ---
DEFAULT_CFM_ALERT_THRESHOLD = 10   # CFM
DEFAULT_CFM_ALERT_DURATION = 60    # seconds — long enough for the ERV to recover from upsets

# The device reports this value for CFM fields when the unit is off or the
# measurement is not yet available.  Treat it as "unknown" rather than a real reading.
CFM_UNKNOWN_SENTINEL = 255

# The device reports 53°C (127.4°F) for temperature fields when idle or when the
# sensor has no valid reading.  Return None so HA shows Unknown rather than a
# spurious spike on the graph.
TEMP_UNKNOWN_SENTINEL = 53

# Key used to store the coordinator in hass.data[DOMAIN][entry_id]
DATA_COORDINATOR = "coordinator"
