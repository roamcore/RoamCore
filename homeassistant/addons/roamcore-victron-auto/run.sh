#!/usr/bin/with-contenv bashio
# Run script for RoamCore Victron Auto add-on

bashio::log.info "Starting RoamCore Victron Auto via run.sh"

# Debug: show SUPERVISOR_TOKEN presence
if [[ -n "${SUPERVISOR_TOKEN:-}" ]]; then
    bashio::log.info "SUPERVISOR_TOKEN is set (length ${#SUPERVISOR_TOKEN})"
else
    bashio::log.warning "SUPERVISOR_TOKEN is NOT set"
fi

# Show MQTT env vars
env | grep -i mqtt || bashio::log.info "No MQTT env vars found"

# Run the main script
exec python3 -m src.main
