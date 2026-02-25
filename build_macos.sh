#!/usr/bin/env bash
#
# HiCeeBox macOS build script
#
# Builds HiCeeBox.app and optionally a DMG. Run from project root.
#
# Important: Activate your conda env first so the script uses the right Python:
#   conda activate HiCeeBox
#   ./build_macos.sh
#
# Usage:
#   ./build_macos.sh           # Build app and DMG
#   ./build_macos.sh --clean   # Clean build (delete build/dist first)
#   ./build_macos.sh --debug   # Build with console window (to see crash messages)
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_NAME="HiCeeBox"
VERSION="0.1.0"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"

# Parse options
CLEAN=false
DEBUG=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)  CLEAN=true; shift ;;
        --debug)  DEBUG=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Ensure we run from project root (directory containing HiCeeBox.spec)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PROJECT_ROOT="$(pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  HiCeeBox macOS Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# --- Step 1: Clean (optional) ---
if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}[1/5] Cleaning build and dist...${NC}"
    rm -rf build dist "$DMG_NAME"
    echo -e "${GREEN}  Done.${NC}"
else
    echo -e "${YELLOW}[1/5] Skipping clean (use --clean to clean first).${NC}"
fi

# --- Step 2: Validate environment ---
echo -e "${YELLOW}[2/5] Checking environment...${NC}"
# Prefer 'python' so conda env's Python is used (conda sets python, not only python3)
PYTHON=""
for cmd in python python3; do
    if command -v "$cmd" &> /dev/null; then
        PYTHON="$(command -v "$cmd")"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo -e "${RED}  Python not found.${NC}"
    exit 1
fi
echo -e "  Using: ${PYTHON}"
"$PYTHON" -c "
import sys
err = []
try: import PySide6
except ImportError: err.append('PySide6')
try: import matplotlib
except ImportError: err.append('matplotlib')
try: import numpy
except ImportError: err.append('numpy')
if err:
    print('Missing:', ', '.join(err))
    sys.exit(1)
import matplotlib
matplotlib.use('QtAgg')
print('OK')
" || { echo -e "${RED}  Missing dependencies in this Python. Activate your conda env and run: pip install PySide6 matplotlib numpy${NC}"; exit 1; }

if ! "$PYTHON" -m PyInstaller --version &> /dev/null; then
    echo -e "${RED}  PyInstaller not found. Install with: pip install pyinstaller${NC}"
    exit 1
fi
echo -e "${GREEN}  Environment OK.${NC}"

# --- Step 3: Patch spec for debug (console) if requested ---
SPEC_BACKUP=""
if [ "$DEBUG" = true ]; then
    echo -e "${YELLOW}[3/5] Building with console (debug mode)...${NC}"
    sed -i.bak 's/^CONSOLE = False$/CONSOLE = True/' HiCeeBox.spec
    SPEC_BACKUP="HiCeeBox.spec.bak"
else
    echo -e "${YELLOW}[3/5] Building application...${NC}"
    # Ensure console is off (no backup so we don't overwrite spec later)
    sed -i '' 's/^CONSOLE = True$/CONSOLE = False/' HiCeeBox.spec 2>/dev/null || true
fi

# --- Step 4: Run PyInstaller ---
echo -e "${YELLOW}[4/5] Running PyInstaller...${NC}"
if ! "$PYTHON" -m PyInstaller --noconfirm HiCeeBox.spec; then
    [ -n "$SPEC_BACKUP" ] && [ -f "$SPEC_BACKUP" ] && mv "$SPEC_BACKUP" HiCeeBox.spec
    echo -e "${RED}  Build failed.${NC}"
    exit 1
fi
[ -n "$SPEC_BACKUP" ] && [ -f "$SPEC_BACKUP" ] && mv "$SPEC_BACKUP" HiCeeBox.spec
echo -e "${GREEN}  App built: dist/${APP_NAME}.app${NC}"

# --- Step 5: Create DMG ---
echo -e "${YELLOW}[5/5] Creating DMG...${NC}"
rm -f "$DMG_NAME"
hdiutil create -volname "$APP_NAME" \
    -srcfolder "dist/${APP_NAME}.app" \
    -ov -format UDZO \
    "$DMG_NAME" || { echo -e "${RED}  DMG creation failed.${NC}"; exit 1; }
echo -e "${GREEN}  DMG created: ${DMG_NAME}${NC}"

# --- Summary ---
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  Build finished successfully${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "  App:  dist/${APP_NAME}.app"
echo "  DMG:  ${DMG_NAME}"
echo ""
du -sh "dist/${APP_NAME}.app" "$DMG_NAME" 2>/dev/null | sed 's/^/  /'
echo ""
echo "  Run app:    open dist/${APP_NAME}.app"
echo "  If it crashes, run from Terminal to see errors:"
echo "    dist/${APP_NAME}.app/Contents/MacOS/HiCeeBox"
echo "  Or rebuild with:  ./build_macos.sh --clean --debug"
echo ""
