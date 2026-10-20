#!/usr/bin/env bash
# Build the Linux AppImage. Requires Python with tkinter and the project requirements installed.
set -euo pipefail

cd "$(dirname "$0")/.."

APP=ps2-memory-card-manager
VERSION="${VERSION:-$(git describe --tags --match 'v*' --always 2>/dev/null || echo dev)}"
ARCH="${ARCH:-x86_64}"

python -m PyInstaller --noconfirm --clean --windowed --onedir \
    --name "$APP" \
    --collect-all libusb_package \
    run_gui.py

rm -rf build/AppDir
mkdir -p build/AppDir/usr/bin
cp -a "dist/$APP/." build/AppDir/usr/bin/
cp packaging/$APP.desktop build/AppDir/
cp packaging/icon.png build/AppDir/$APP.png
ln -s $APP.png build/AppDir/.DirIcon
cat > build/AppDir/AppRun <<APPRUN
#!/bin/sh
HERE="\$(dirname "\$(readlink -f "\$0")")"
exec "\$HERE/usr/bin/$APP" "\$@"
APPRUN
chmod +x build/AppDir/AppRun

APPIMAGETOOL="${APPIMAGETOOL:-build/appimagetool-$ARCH.AppImage}"
if [ ! -x "$APPIMAGETOOL" ]; then
    curl -fsSL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

# Extract-and-run avoids needing FUSE (CI runners, containers)
APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$ARCH" VERSION="$VERSION" \
    "$APPIMAGETOOL" build/AppDir "dist/$APP-$VERSION-$ARCH.AppImage"

echo "Built dist/$APP-$VERSION-$ARCH.AppImage"
