#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Config (edit if your layout differs)
# -----------------------------
APP_NAME="PoseApp"
ENTRYPOINT="app/main.py"                 # your Python entry script
ICON_PATH="assets/icons/poseapp.png"     # optional; a placeholder is made if missing
DOCS_SRC="docs/site/html"                # Sphinx output folder to bundle

# PyInstaller extra data (src:dest inside bundle)
EXTRA_DATA=(
  "assets:assets"
  "models:models"
  "${DOCS_SRC}:docs_site"
)

# -----------------------------
# Helper: echo step title
# -----------------------------
step() { printf "\n\033[1;36m==> %s\033[0m\n" "$*"; }

# -----------------------------
# Pre-flight checks
# -----------------------------
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found"; exit 1
fi

if ! command -v appimagetool >/dev/null 2>&1; then
  echo "appimagetool not found in PATH. See setup instructions to install it under ~/tools and add to PATH."
  exit 1
fi

if [[ ! -f "$ENTRYPOINT" ]]; then
  echo "ENTRYPOINT not found: $ENTRYPOINT"; exit 1
fi

# Warn if not x86_64 (AppImage target); still allow build
ARCH="$(uname -m)"
if [[ "$ARCH" != "x86_64" ]]; then
  echo "WARNING: host arch is '$ARCH'. For widest compatibility (Fedora/Ubuntu), build on x86_64."
fi

# -----------------------------
# Python venv & deps
# -----------------------------
if [[ ! -d ".venv" ]]; then
  step "Creating venv"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip wheel setuptools

step "Installing runtime & build deps"
python -m pip install -r requirements.txt || true
python -m pip install "pyinstaller==6.*" pyinstaller-hooks-contrib

# -----------------------------
# Clean previous builds
# -----------------------------
step "Cleaning old build artifacts"
rm -rf build dist packaging/linux/AppDir "${APP_NAME}-x86_64.AppImage" || true

# -----------------------------
# PyInstaller build
# -----------------------------
step "Running PyInstaller"
PYI_ARGS=(
  "$ENTRYPOINT"
  --name "$APP_NAME"
  --noconfirm
  --clean
  --windowed
  --collect-all cv2
  --collect-all mediapipe
  --collect-all tflite_runtime
  --collect-all PySide6
)

# add data paths
for spec in "${EXTRA_DATA[@]}"; do
  PYI_ARGS+=( --add-data "$spec" )
done

pyinstaller "${PYI_ARGS[@]}"

# -----------------------------
# Stage AppDir
# -----------------------------
APPDIR="packaging/linux/AppDir"
step "Staging AppDir at $APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy frozen app (directory build)
cp -a "dist/${APP_NAME}/." "$APPDIR/usr/bin/"

# Desktop file
cat > "$APPDIR/usr/share/applications/${APP_NAME,,}.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Offline pose estimation (Freestyle & Guided) with MoveNet/MediaPipe
Exec=${APP_NAME}
Icon=${APP_NAME,,}
Terminal=false
Categories=Education;Science;Graphics;Qt;
DESK

# Icon (make placeholder if missing)
ICON_DST="$APPDIR/usr/share/icons/hicolor/256x256/apps/${APP_NAME,,}.png"
if [[ -f "$ICON_PATH" ]]; then
  cp "$ICON_PATH" "$ICON_DST"
else
  if command -v convert >/dev/null 2>&1; then
    convert -size 256x256 xc:"#2b2b2b" -fill white -pointsize 56 \
      -gravity center -annotate 0 "${APP_NAME:0:4}" "$ICON_DST"
  else
    # last resort tiny placeholder
    printf '\211PNG\r\n\032\n' > "$ICON_DST" || true
  fi
fi

# AppRun launcher
cat > "$APPDIR/AppRun" <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"

# Prefer XCB on Wayland issues
export QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-xcb}

# Bundle-friendly paths
export LD_LIBRARY_PATH="$HERE/usr/bin:$LD_LIBRARY_PATH"
export PYTHONPATH="$HERE/usr/bin:$PYTHONPATH"

exec "$HERE/usr/bin/PoseApp" "$@"
RUN
chmod +x "$APPDIR/AppRun"

# AppImage conventions
ln -sf "usr/share/applications/${APP_NAME,,}.desktop" "$APPDIR/${APP_NAME,,}.desktop"
ln -sf "usr/share/icons/hicolor/256x256/apps/${APP_NAME,,}.png" "$APPDIR/${APP_NAME,,}.png"

# -----------------------------
# Build AppImage
# -----------------------------
step "Building AppImage"
appimagetool "$APPDIR" "${APP_NAME}-x86_64.AppImage"

step "Done"
echo "Output: $(pwd)/${APP_NAME}-x86_64.AppImage"
