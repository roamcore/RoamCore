ARG BUILD_FROM
FROM ${BUILD_FROM}

# RoamCore OTA add-on
# Stdlib-only Python 3 (no requests, no extra deps). Talks to api.github.com
# over HTTPS using urllib.request. Uses s6-overlay services from the base
# image to supervise the long-running daemon.
RUN apk add --no-cache python3 bash jq coreutils tzdata \
    && rm -rf /var/cache/apk/*

WORKDIR /app
COPY rootfs /

# s6 service definition lives under /etc/services.d/roamcore_ota/run
# which is what the base image picks up. Make scripts executable.
RUN chmod a+x /usr/bin/roamcore-otad \
    && chmod a+x /etc/services.d/roamcore_ota/run \
    && chmod a+x /etc/services.d/roamcore_ota/finish

# Healthcheck exposed via the HA Supervisor container API.
HEALTHCHECK --interval=60s --timeout=5s --start-period=20s --retries=3 \
  CMD pgrep -f "roamcore-otad" >/dev/null || exit 1

LABEL io.hass.name="RoamCore OTA" \
      io.hass.description="GitHub-based OTA update channel for RoamCore (stable/beta/nightly) with rollback-aware snapshot history" \
      io.hass.type="addon" \
      io.hass.version="0.1.0"