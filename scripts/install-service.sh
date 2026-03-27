#!/bin/bash
# ResuMatch AI — Cross-platform service installer
# Detects macOS vs Linux and runs the appropriate installer.
# For Windows, run: powershell -ExecutionPolicy Bypass -File scripts/install-windows.ps1

set -e

OS="$(uname -s)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "$OS" in
    Darwin)
        echo "Detected macOS"
        bash "${SCRIPT_DIR}/install-macos.sh"
        ;;
    Linux)
        echo "Detected Linux — using systemd"
        # Create a systemd user service
        SERVICE_DIR="$HOME/.config/systemd/user"
        mkdir -p "$SERVICE_DIR"

        PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
        BACKEND_DIR="${PROJECT_DIR}/backend"
        VENV_PYTHON="${BACKEND_DIR}/venv/bin/python"

        if [ ! -f "$VENV_PYTHON" ]; then
            echo "❌ Virtual environment not found. Set it up first."
            exit 1
        fi

        cat > "${SERVICE_DIR}/resumatch-ai.service" << EOF
[Unit]
Description=ResuMatch AI — Local RAG Pipeline
After=network.target

[Service]
Type=simple
WorkingDirectory=${BACKEND_DIR}
ExecStart=${VENV_PYTHON} main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

        systemctl --user daemon-reload
        systemctl --user enable resumatch-ai
        systemctl --user start resumatch-ai
        echo "✅ systemd service installed and started"
        echo "   Status:  systemctl --user status resumatch-ai"
        echo "   Logs:    journalctl --user -u resumatch-ai -f"
        echo "   Stop:    systemctl --user stop resumatch-ai"
        ;;
    *)
        echo "❌ Unsupported OS: $OS"
        echo "   For Windows, run: powershell -ExecutionPolicy Bypass -File scripts/install-windows.ps1"
        exit 1
        ;;
esac
