#!/usr/bin/env bash
set -euo pipefail

RASP="rasp"
REMOTE_DIR="~/crypto-tracker-diy"
SCRIPT="refresh_ink.py"

echo ">> Syncing project to $RASP:$REMOTE_DIR/"
ssh "$RASP" "mkdir -p $REMOTE_DIR/logos"
scp "$SCRIPT" "$RASP:$REMOTE_DIR/"
scp logos/*.png "$RASP:$REMOTE_DIR/logos/"

echo ">> Installing crontab (every 10 min)..."
CRON_CMD="cd $REMOTE_DIR && venv/bin/python $SCRIPT >> $REMOTE_DIR/cron.log 2>&1"
ssh "$RASP" "(crontab -l 2>/dev/null | grep -v 'refresh_ink.py'; echo '*/10 * * * * $CRON_CMD') | crontab -"

echo ">> Running now..."
ssh -t "$RASP" "cd $REMOTE_DIR && venv/bin/python $SCRIPT"

echo ">> Done. Crontab will refresh every 10 minutes."
