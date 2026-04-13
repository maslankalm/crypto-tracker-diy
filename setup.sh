#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git

echo "==> Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

if [ ! -d "e-Paper" ]; then
    echo "==> Cloning Waveshare e-Paper driver..."
    git clone --depth 1 https://github.com/waveshare/e-Paper.git e-Paper
else
    echo "==> Waveshare e-Paper driver already present, pulling latest..."
    git -C e-Paper pull
fi

echo "==> Linking waveshare_epd library..."
ln -sf e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd waveshare_epd

echo "==> Installing crontab (every 10 min)..."
CRON_CMD="cd $(pwd) && venv/bin/python refresh_ink.py >> $(pwd)/cron.log 2>&1"
(crontab -l 2>/dev/null | grep -v 'refresh_ink.py'; echo "*/10 * * * * $CRON_CMD") | crontab -

echo "==> Setup complete. Crontab will refresh the display every 10 minutes."
