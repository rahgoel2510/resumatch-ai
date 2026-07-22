#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RG Aide — Build Script
# Copyright (c) 2026 Rahul Goel. MIT License.
# ═══════════════════════════════════════════════════════════════
#
# USAGE:
#   ./build.sh          Compile SCSS → CSS (development)
#   ./build.sh watch    Watch for changes & auto-compile
#   ./build.sh prod     Production build: compile + obfuscate + package
#
# REQUIRES: Node.js (for npx sass and npx terser)
# ═══════════════════════════════════════════════════════════════

set -e
cd "$(dirname "$0")"

# ─── Development: just compile SCSS ─────────────────────────────
if [ "$1" = "watch" ]; then
  echo "👀 Watching for changes (Ctrl+C to stop)..."
  npx sass --watch aide.scss:aide.css options.scss:options.css --no-source-map --style=expanded
  exit 0
fi

if [ "$1" != "prod" ]; then
  echo "🎨 Compiling SCSS..."
  npx sass aide.scss aide.css --no-source-map --style=expanded
  npx sass options.scss options.css --no-source-map --style=expanded
  echo "✓ aide.css compiled"
  echo "✓ options.css compiled"
  echo "Done! (dev build)"
  exit 0
fi

# ─── Production: compile + obfuscate + package ──────────────────
echo "🚀 PRODUCTION BUILD"
echo "==================="
echo ""

# Step 1: Compile SCSS → compressed CSS
echo "[1/4] Compiling SCSS (compressed)..."
npx sass aide.scss aide.css --no-source-map --style=compressed
npx sass options.scss options.css --no-source-map --style=compressed
echo "  ✓ CSS compiled & minified"

# Step 2: Obfuscate JavaScript (non-readable, mangled variables)
echo "[2/4] Obfuscating JavaScript..."
npx terser aide.js \
  --compress drop_console=true,passes=3 \
  --mangle toplevel=true,reserved='["chrome"]' \
  --output aide.js.tmp \
  --ecma 2020

npx terser background.js \
  --compress drop_console=true \
  --mangle \
  --output background.js.tmp \
  --ecma 2020

npx terser options.js \
  --compress drop_console=true,passes=3 \
  --mangle toplevel=true,reserved='["chrome"]' \
  --output options.js.tmp \
  --ecma 2020

# Replace originals with obfuscated versions
mv aide.js.tmp aide.js
mv background.js.tmp background.js
mv options.js.tmp options.js
echo "  ✓ JS obfuscated (variable names mangled, console logs stripped)"

# Step 3: Create production package (dist folder)
echo "[3/4] Packaging..."
DIST_DIR="../dist-extension"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# Copy only production files (no .scss source, no build script)
cp manifest.json "$DIST_DIR/"
cp sidepanel.html "$DIST_DIR/"
cp aide.css "$DIST_DIR/"
cp aide.js "$DIST_DIR/"
cp background.js "$DIST_DIR/"
cp options.html "$DIST_DIR/"
cp options.css "$DIST_DIR/"
cp options.js "$DIST_DIR/"
cp icon16.png "$DIST_DIR/"
cp icon32.png "$DIST_DIR/"
cp icon48.png "$DIST_DIR/"
cp icon128.png "$DIST_DIR/"
cp LICENSE "$DIST_DIR/"

echo "  ✓ Packaged to: $DIST_DIR/"

# Step 4: Report sizes
echo "[4/4] Size report:"
echo "  ─────────────────────────────────"
for f in "$DIST_DIR"/*.{js,css,html,json}; do
  [ -f "$f" ] && printf "  %-20s %s\n" "$(basename "$f")" "$(wc -c < "$f" | tr -d ' ') bytes"
done
echo "  ─────────────────────────────────"
TOTAL=$(find "$DIST_DIR" -type f -exec cat {} + | wc -c | tr -d ' ')
echo "  TOTAL: ${TOTAL} bytes"
echo ""
echo "✅ Production build complete!"
echo "   Load '$DIST_DIR/' as unpacked extension in Chrome."
echo ""
echo "⚠️  NOTE: Source .js files in chrome-extension/ are now obfuscated."
echo "   To restore readable source, run: git checkout -- *.js"
