ARG BUILD_FROM
# Use ${BUILD_FROM} (braced) for consistency with the rest of the add-on
# fleet and to match the variable expansion that the HA add-on build pipeline
# expects. The unbraced form fails with "base name ($BUILD_FROM) should not
# be blank" when BUILD_FROM is unset (eg. ad-hoc `docker build` smoke runs).
FROM ${BUILD_FROM}

RUN apk add --no-cache bash curl openssl jq python3

COPY rootfs /
RUN chmod +x /usr/bin/roamcore-traccar-init
