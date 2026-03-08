ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.20
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY run.sh /
RUN chmod a+x /run.sh

CMD ["/run.sh"]

