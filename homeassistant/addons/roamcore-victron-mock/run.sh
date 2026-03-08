#!/usr/bin/with-contenv bashio

bashio::log.info "Starting RoamCore Victron Mock (DEV)"

exec python3 -m src.main

