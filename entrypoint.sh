#!/bin/sh
set -e
mkdir -p /app/raspberry/Logs /app/raspberry/Temp
chown -R logger:logger /app/raspberry/Logs /app/raspberry/Temp
exec gosu logger python3 main.py "$@"
