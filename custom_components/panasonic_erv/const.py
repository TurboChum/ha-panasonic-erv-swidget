DOMAIN = "panasonic_erv"
DEFAULT_NAME = "Panasonic ERV"
DEFAULT_POLL_INTERVAL = 60
DEFAULT_RETRY_COUNT = 3
DEFAULT_VERIFY_DELAY = 2
DEFAULT_BOOST_RECOVERY = True

CONF_DEVICE_URL = "device_url"
CONF_DEVICE_NAME = "device_name"
CONF_POLL_INTERVAL = "poll_interval"
CONF_RETRY_COUNT = "retry_count"
CONF_VERIFY_DELAY = "verify_delay"
CONF_BOOST_RECOVERY = "boost_recovery"

CONF_MAC = "mac"
CONF_FW_VERSION = "fw_version"
CONF_MODEL_NAME = "model_name"

CONF_CFM_ALERT_THRESHOLD = "cfm_alert_threshold"
CONF_CFM_ALERT_DURATION = "cfm_alert_duration"
DEFAULT_CFM_ALERT_THRESHOLD = 10   # CFM
DEFAULT_CFM_ALERT_DURATION = 60    # seconds

# Sentinel value the device reports for CFM when not running or measurement unavailable
CFM_UNKNOWN_SENTINEL = 255

DATA_COORDINATOR = "coordinator"
