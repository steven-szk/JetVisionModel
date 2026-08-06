#!/usr/bin/env bash
# Stop the JetVision app gracefully.
#
# Sends SIGTERM, which main.py turns into a clean shutdown (REBOOT the ESP, release
# the camera, stop the web control panel). Works whether the app is running under
# systemd (jetvision.service) or was started by hand with `python main.py`.
#
#   ./kill.sh
set -uo pipefail

SERVICE=defectdetect

# 1) Prefer systemd if the unit is installed.
if systemctl list-unit-files 2>/dev/null | grep -q "^${SERVICE}\.service"; then
    if systemctl is-active --quiet "$SERVICE"; then
        echo "Stopping ${SERVICE}.service ..."
        sudo systemctl stop "$SERVICE"
        echo "Stopped."
    else
        echo "${SERVICE}.service is installed but not running."
    fi
    exit 0
fi

# 2) Fallback: started by hand -> SIGTERM the main.py process.
if pkill -TERM -f "main\.py"; then
    echo "Sent SIGTERM to main.py."
else
    echo "No running main.py found."
fi
