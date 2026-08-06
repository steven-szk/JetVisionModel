#!/usr/bin/env bash
# (Re)start the DefectDetect app: stop whatever is running, then start the service.
#
#   ./run.sh
set -uo pipefail

# Work from the script's own folder, so it runs no matter where you call it from.
cd "$(dirname "$0")"

# 1) Stop any running instance (systemd service OR a hand-started main.py).
bash kill.sh

# 2) Start it via systemd.
sudo systemctl start defectdetect
echo "Started. Follow the logs with:  journalctl -u defectdetect -f"
