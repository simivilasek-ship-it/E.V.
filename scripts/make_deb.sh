#!/usr/bin/env bash
# Build a minimal .deb package for JARVIS.
# Usage: bash scripts/make_deb.sh
# Requires: dpkg-deb (standard on Debian/Ubuntu)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

VERSION=$(python3 -c "from config import __version__; print(__version__)" 2>/dev/null || echo "5.11.0")
PKG="jarvis_${VERSION}_amd64"
BUILD_DIR="/tmp/${PKG}"

echo "Building JARVIS v${VERSION} .deb..."
echo "  Build dir: ${BUILD_DIR}"

# Create package directory structure
rm -rf "$BUILD_DIR"
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/local/lib/jarvis"
mkdir -p "${BUILD_DIR}/usr/local/bin"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/doc/jarvis"
mkdir -p "${BUILD_DIR}/etc/jarvis"

# control file
cat > "${BUILD_DIR}/DEBIAN/control" << EOF
Package: jarvis
Version: ${VERSION}
Section: misc
Priority: optional
Architecture: amd64
Maintainer: simivilasek-ship-it
Depends: python3 (>= 3.11), python3-pip, nodejs, ffmpeg
Description: Local AI assistant for Linux
 JARVIS is a local-first AI assistant with Work Timeline,
 agent graph, MCP tools, and live PC context.
 Web UI at http://localhost:8002/app
EOF

# postinst — install Python deps and enable systemd unit
cat > "${BUILD_DIR}/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
cd /usr/local/lib/jarvis
pip3 install -r requirements.txt --quiet 2>/dev/null || true
pip3 install mcp --quiet 2>/dev/null || true
# Enable systemd user service (for current user at login)
if [ -f /usr/local/lib/jarvis/desktop/jarvis.service ]; then
  mkdir -p "$HOME/.config/systemd/user"
  sed "s|@JARVIS_DIR@|/usr/local/lib/jarvis|g" \
      /usr/local/lib/jarvis/desktop/jarvis.service \
      > "$HOME/.config/systemd/user/jarvis.service" 2>/dev/null || true
fi
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"

# Copy project files (skip venv, .git, web_dist, etc.)
rsync -a --exclude='.git' \
         --exclude='venv' \
         --exclude='.venv' \
         --exclude='web_dist' \
         --exclude='web/node_modules' \
         --exclude='__pycache__' \
         --exclude='*.pyc' \
         --exclude='.claude' \
         --exclude='web_vite_backup' \
         "${ROOT}/" "${BUILD_DIR}/usr/local/lib/jarvis/"

# Launcher script
cat > "${BUILD_DIR}/usr/local/bin/jarvis" << 'EOF'
#!/bin/sh
exec python3 /usr/local/lib/jarvis/jarvis.py "$@"
EOF
chmod 755 "${BUILD_DIR}/usr/local/bin/jarvis"

# .desktop file
cat > "${BUILD_DIR}/usr/share/applications/jarvis.desktop" << EOF
[Desktop Entry]
Name=JARVIS
Comment=Local AI assistant for Linux
Exec=jarvis
Icon=/usr/local/lib/jarvis/jarvis.png
Terminal=false
Type=Application
Categories=Utility;
EOF

# changelog
cp "${ROOT}/CHANGELOG.md" "${BUILD_DIR}/usr/share/doc/jarvis/changelog.md" 2>/dev/null || true

# Build .deb
OUTPUT="${ROOT}/${PKG}.deb"
dpkg-deb --build "$BUILD_DIR" "$OUTPUT"
echo "✓ Built: ${OUTPUT}"
echo "  Install with: sudo dpkg -i ${PKG}.deb"
