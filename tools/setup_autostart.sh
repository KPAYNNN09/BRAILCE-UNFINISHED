#!/bin/bash
# ==============================================================================
# Brailce – Standalone Autostart Setup Script for Raspberry Pi 5
# ==============================================================================
# This script configures Brailce to automatically run on boot as a background
# systemd service. Once installed, your Raspberry Pi 5 will operate completely
# standalone — no laptop, no PuTTY, and no monitor/terminal needed!
#
# Usage:
#   bash tools/setup_autostart.sh            # Install & enable autostart
#   bash tools/setup_autostart.sh --status   # Check service status
#   bash tools/setup_autostart.sh --logs     # View live application logs
#   bash tools/setup_autostart.sh --remove   # Disable & uninstall service
# ==============================================================================

set -e

SERVICE_NAME="brailce.service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

# Locate project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_EXEC="$(which python3)"

# Handle command-line flags
case "$1" in
    --status)
        echo "=== Brailce Service Status ==="
        sudo systemctl status "${SERVICE_NAME}" --no-pager
        exit 0
        ;;
    --logs)
        echo "=== Following Live Brailce Logs (Ctrl+C to stop) ==="
        sudo journalctl -u "${SERVICE_NAME}" -f
        exit 0
        ;;
    --remove)
        echo "Stopping and disabling ${SERVICE_NAME}..."
        sudo systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
        sudo systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
        sudo rm -f "${SERVICE_FILE}"
        sudo systemctl daemon-reload
        echo "✓ Brailce standalone autostart has been removed."
        exit 0
        ;;
esac

echo "=================================================================="
echo "    Brailce – Raspberry Pi 5 Standalone Autostart Installer"
echo "=================================================================="
echo "Project Directory : ${PROJECT_ROOT}"
echo "Python Executable : ${PYTHON_EXEC}"
echo ""

# Ensure we have root or sudo privileges
if [ "$EUID" -ne 0 ] && ! command -v sudo >/dev/null 2>&1; then
    echo "ERROR: This script requires root or sudo privileges to create a system service."
    exit 1
fi

# Check for Ollama to set dependency
OLLAMA_DEP=""
if systemctl list-unit-files | grep -q "ollama.service"; then
    OLLAMA_DEP="Wants=ollama.service\nAfter=ollama.service"
    echo "✓ Detected local Ollama service — added to startup order."
fi

# Write systemd service file
echo "Writing ${SERVICE_FILE}..."
sudo bash -c "cat > ${SERVICE_FILE}" <<EOF
[Unit]
Description=Brailce Assistive Device Standalone Service
After=network.target sound.target multi-user.target
${OLLAMA_DEP}

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_ROOT}
ExecStart=${PYTHON_EXEC} main.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable service
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling ${SERVICE_NAME} for automatic start on boot..."
sudo systemctl enable "${SERVICE_NAME}"

echo ""
echo "=================================================================="
echo "  ✓ Brailce Autostart Configured Successfully!"
echo "=================================================================="
echo ""
echo "What happens now?"
echo "1. Every time you power on the Raspberry Pi 5 (battery or wall adapter):"
echo "   - Pi 5 boots Linux."
echo "   - The 3.5\" screen will turn on (white for ~10s during boot)."
echo "   - Brailce will launch automatically, taking over the screen and audio."
echo "   - Any connected USB keyboard will accept input immediately."
echo ""
echo "Useful Commands:"
echo "  • Start it right now:   sudo systemctl start ${SERVICE_NAME}"
echo "  • Stop it:              sudo systemctl stop ${SERVICE_NAME}"
echo "  • Check if running:     bash tools/setup_autostart.sh --status"
echo "  • View live logs:       bash tools/setup_autostart.sh --logs"
echo "  • Remove autostart:     bash tools/setup_autostart.sh --remove"
echo "=================================================================="
