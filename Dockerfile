FROM python:3.11-slim

WORKDIR /app

COPY raspberry/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY raspberry/ ./raspberry/

# Create a non-root user; add to dialout for serial port access
RUN useradd -m logger && usermod -aG dialout logger && \
    mkdir -p /app/raspberry/Logs /app/raspberry/Temp && \
    chown -R logger:logger /app/raspberry/Logs /app/raspberry/Temp
USER logger

WORKDIR /app/raspberry

ENTRYPOINT ["python3", "main.py"]
