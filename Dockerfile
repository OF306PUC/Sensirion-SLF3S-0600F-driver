FROM python:3.11-slim

WORKDIR /app

COPY raspberry/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY raspberry/ ./raspberry/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN useradd -m logger && usermod -aG dialout logger

WORKDIR /app/raspberry

ENTRYPOINT ["/entrypoint.sh"]
