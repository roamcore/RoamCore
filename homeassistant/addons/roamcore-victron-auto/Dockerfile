ARG BUILD_FROM
FROM ${BUILD_FROM}

# Simple Python-based add-on
RUN apk add --no-cache python3 py3-pip

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python3", "-m", "src.main"]
