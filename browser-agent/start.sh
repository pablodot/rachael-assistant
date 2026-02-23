#!/bin/bash
set -e

# Arrancar display virtual si no está corriendo
if ! pgrep -x Xvfb > /dev/null; then
    Xvfb :99 -screen 0 1920x1080x24 &
    sleep 1
fi

export DISPLAY=:99

cd "$(dirname "$0")"
source .venv/bin/activate
python main.py
