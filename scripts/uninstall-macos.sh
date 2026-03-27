#!/bin/bash
# ResuMatch AI — macOS Service Uninstaller

SERVICE_NAME="com.resumatch.ai"
PLIST_PATH="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"

echo "🎯 ResuMatch AI — Uninstalling macOS service..."

if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm -f "$PLIST_PATH"
    echo "✅ Service removed."
else
    echo "ℹ️  Service not installed."
fi
