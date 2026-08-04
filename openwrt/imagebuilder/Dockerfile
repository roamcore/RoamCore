# RoamCore OpenWrt Image Builder
#
# This Dockerfile wraps the official OpenWrt Image Builder in a pinned
# version so the RoamCore images are reproducible bit-for-bit. Pinning
# is essential: OpenWrt package feeds and signing keys change between
# releases, which would otherwise break the "same input → same sha256"
# acceptance criterion.
#
# Usage:
#   docker build -t roamcore-imagebuilder:24.10.4 .
#   docker run --rm -v "$PWD/../flash:/out" roamcore-imagebuilder:24.10.4
#
# Why we don't build directly on the host:
#   - Image Builder requires glibc Linux (not musl). macOS / WSL hosts
#     need a container to get a stable toolchain.
#   - The container pins the entire build environment, including wget,
#     tar, and libarchive versions, all of which influence the final
#     image bytes.
#
# OpenWrt Image Builder reference:
#   https://openwrt.org/docs/guide-user/additional-software/imagebuilder

FROM ubuntu:22.04

ARG OPENWRT_VERSION=24.10.4
ARG TARGET=x86_64

ENV DEBIAN_FRONTEND=noninteractive \
    OPENWRT_VERSION=${OPENWRT_VERSION} \
    OPENWRT_TARGET=${TARGET}

# Install only the packages Image Builder needs. Keep the list minimal so
# the base layer is stable across rebuilds (no spurious apt upgrades).
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        bash \
        xz-utils \
        git \
        file \
        libarchive-tools && \
    rm -rf /var/lib/apt/lists/*

# Download Image Builder once, into /opt. We pin by version so
# future Image Builder re-releases of the same version (which OpenWrt
# sometimes does for security fixes) cannot silently change our output.
WORKDIR /opt
RUN IB_URL="https://downloads.openwrt.org/releases/${OPENWRT_VERSION}/targets/${OPENWRT_TARGET}/openwrt-imagebuilder-${OPENWRT_VERSION}-${OPENWRT_TARGET}.Linux-x86_64.tar.xz" && \
    echo "Downloading ${IB_URL}" && \
    curl -fsSL -o ib.tar.xz "${IB_URL}" && \
    tar -xJf ib.tar.xz && \
    rm ib.tar.xz && \
    mv openwrt-imagebuilder-* openwrt-ib && \
    echo "Image Builder ready: $(ls -d /opt/openwrt-ib)"

# Copy the RoamCore bake-in scripts and per-target manifests.
COPY bake/ /opt/roamcore-bake/
COPY manifests/ /opt/roamcore-bake/manifests/
COPY build.sh /usr/local/bin/roamcore-build
RUN chmod +x /usr/local/bin/roamcore-build

WORKDIR /opt/openwrt-ib
ENTRYPOINT ["/usr/local/bin/roamcore-build"]