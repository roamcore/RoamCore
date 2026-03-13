FROM ghcr.io/home-assistant/amd64-base:3.20

RUN apk add --no-cache bash nginx curl jq

COPY rootfs /

RUN chmod +x /etc/services.d/roamcore-traccar-proxy/run \
  && chmod +x /usr/bin/roamcore-traccar-proxy

