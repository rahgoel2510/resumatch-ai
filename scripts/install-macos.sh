#!/bin/bash
# ============================================================
# ResuMatch AI — macOS Background Service Installer
# Uses launchd to run the RAG pipeline as a persistent service
# that starts on login and restarts on crash.
# ============================================================

set -e

SERVICE_NAME="com.resumatch.ai"
PLIST_PATH="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="${PROJECT_DIR}/backend"
VENV_PYTHON="${BACKEND_DIR}/venv/bin/python"
LOG_DIR="${BACKEND_DIR}/logs"

echo "🎯 ResuMatch AI — macOS Service Installer"
echo "==========================================="
echo "Backend:  ${BACKEND_DIR}"
echo "Python:   ${VENV_PYTHON}"
echo ""

# Check venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment not found at ${VENV_PYTHON}"
    echo "   Run: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Create log directory
mkdir -p "$LOG_DIR"

# Stop existing service if running
if launchctl list | grep -q "$SERVICE_NAME" 2>/dev/null; then
    echo "Stopping existing service..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# Write the plist
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${SERVICE_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${VENV_PYTHON}</string>
        <string>main.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${BACKEND_DIR}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>ThrottleInterval</key>
    <integer>10</integer>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/resumatch.log</string>

    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/resumatch.error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

echo "✅ Plist written to ${PLIST_PATH}"

# Load the service
launchctl load "$PLIST_PATH"
echo "✅ Service loaded and started"
echo ""
echo "📋 Useful commands:"
echo "   Status:   launchctl list | grep resumatch"
echo "   Logs:     tail -f ${LOG_DIR}/resumatch.log"
echo "   Stop:     launchctl unload ${PLIST_PATH}"
echo "   Restart:  launchctl unload ${PLIST_PATH} && launchctl load ${PLIST_PATH}"
echo ""
echo "The service will:"
echo "  • Start automatically on login"
echo "  • Restart if it crashes"
echo "  • Auto re-index when you add/update resumes in resume_data/"
