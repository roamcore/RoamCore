ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python deps.
# NOTE: Alpine 3.20+ enforces PEP 668 (externally-managed-environment), so
# `pip install` without --break-system-packages fails. This matches the
# pattern used by roamcore-victron-{auto,mock}.
RUN apk add --no-cache python3 py3-pip sqlite
RUN pip3 install --break-system-packages --no-cache-dir aiohttp

WORKDIR /app
COPY run.py /app/run.py

CMD ["python3", "/app/run.py"]
