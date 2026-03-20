ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip sqlite
RUN pip3 install --no-cache-dir aiohttp

WORKDIR /app
COPY run.py /app/run.py

CMD ["python3", "/app/run.py"]

