# NOTE: not executed in this study (no Docker daemon was available in the authoring environment).
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends mosquitto make && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/pbti
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["make", "test", "campaign", "perf", "e2e", "analysis"]
