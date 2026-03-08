ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.20
FROM ${BUILD_FROM}

# Simple Python-based add-on
RUN apk add --no-cache python3 py3-pip

WORKDIR /usr/src/app
COPY requirements.txt ./

# Alpine/Python may enforce PEP 668 (externally managed env). For add-on containers
# we can safely install into the system site-packages.
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python3", "-m", "src.main"]
