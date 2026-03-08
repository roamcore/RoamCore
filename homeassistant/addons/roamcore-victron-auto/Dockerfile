ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.20
FROM ${BUILD_FROM}

# Simple Python-based add-on
RUN apk add --no-cache python3 py3-pip

WORKDIR /usr/src/app
COPY requirements.txt ./

# Alpine/Python may enforce PEP 668 (externally managed env). For add-on containers
# we can safely install into the system site-packages.
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Force cache bust by echoing BUILD_VERSION (which changes with version bumps)
ARG BUILD_VERSION=dev
RUN echo "Building version: ${BUILD_VERSION}"

COPY src/ ./src/
COPY run.sh /

RUN chmod a+x /run.sh

CMD ["/run.sh"]
