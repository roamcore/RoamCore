DOMAIN = "roamcore"

CONF_CONTRACT_VERSION = "contract_version"
DEFAULT_CONTRACT_VERSION = 1

# The HTTP header that every RoamCore API response emits, so the
# agent can detect a contract bump BEFORE parsing the body (the
# body shape can change between versions; the header is the canary).
# The agent sees this header on EVERY endpoint — /summary, /skill,
# /rc_dump, /timeseries/*, /automation/*, /diagnostics,
# /system/summary, /update, /pmtiles/* — and the value is the
# integer contract version (currently 1).
ROAMCORE_CONTRACT_HEADER = "X-RoamCore-Contract"

# Options
CONF_OPENCLAW_API_ENABLED = "openclaw_api_enabled"
CONF_OPENCLAW_API_REQUIRES_AUTH = "openclaw_api_requires_auth"

DEFAULT_OPENCLAW_API_ENABLED = True
# MVP: default unauthenticated for isolated LAN use. Users can harden via options.
DEFAULT_OPENCLAW_API_REQUIRES_AUTH = False

# Setup wizard / optional integrations (stored in config entry options)
CONF_TRACCAR_USER_TOKEN = "traccar_user_token"
CONF_IOVERLANDER_API_KEY = "ioverlander_api_key"

CONF_AUTO_PROVISION_ASSETS = "auto_provision_assets"
DEFAULT_AUTO_PROVISION_ASSETS = True
CONF_PROVISION_REF = "provision_ref"
DEFAULT_PROVISION_REF = "main"
