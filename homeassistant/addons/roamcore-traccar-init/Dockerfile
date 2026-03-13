ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache bash curl openssl jq

COPY rootfs /
RUN chmod +x /usr/bin/roamcore-traccar-init
