#!/usr/bin/env bash
# SaveYourKDEDesign — Installation ins Benutzerverzeichnis
set -e

# Stable paths keep existing installations and desktop entries upgradeable.
APP_DIR="$HOME/.local/share/savedesktopdesign"
BIN_DIR="$HOME/.local/bin"
DESKTOP_FILE="$HOME/.local/share/applications/savedesktopdesign.desktop"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

REPO_URL="https://github.com/redsoul1905/SaveYourKDEDesign.git"
LEGACY_REPO_URL="https://github.com/redsoul1905/Savedesktopdesign.git"

if [[ "$1" == "--uninstall" ]]; then
    rm -rf "$APP_DIR"
    rm -f "$BIN_DIR/savedesktopdesign" "$BIN_DIR/saveyourkdedesign" "$DESKTOP_FILE"
    echo "SaveYourKDEDesign wurde entfernt. / SaveYourKDEDesign has been removed."
    exit 0
fi

if [[ "$1" == "--update" ]]; then
    echo "Updating SaveYourKDEDesign ..."
    if [[ -d "$SRC_DIR/.git" ]] && command -v git >/dev/null; then
        if ! git -C "$SRC_DIR" diff --quiet || ! git -C "$SRC_DIR" diff --cached --quiet; then
            echo "Local changes in $SRC_DIR — commit or stash them first:"
            echo "  git -C \"$SRC_DIR\" stash"
            exit 1
        fi
        if ! git -C "$SRC_DIR" pull --ff-only; then
            echo "git pull failed (diverged branch?). Fix the repo manually or re-clone."
            exit 1
        fi
    else
        echo "No git repository found — downloading a fresh copy ..."
        command -v git >/dev/null || { echo "git is required for updating."; exit 1; }
        if ! git ls-remote "$REPO_URL" HEAD >/dev/null 2>&1; then
            REPO_URL="$LEGACY_REPO_URL"
        fi
        TMP_DIR="$(mktemp -d)"
        git clone --depth 1 "$REPO_URL" "$TMP_DIR/repo"
        cp -f "$TMP_DIR/repo/savedesktopdesign.py" "$TMP_DIR/repo/install.sh" "$SRC_DIR/"
        chmod +x "$SRC_DIR/install.sh"
        rm -rf "$TMP_DIR"
    fi
    exec "$SRC_DIR/install.sh"   # frisch installieren mit neuer Version
fi

# Abhängigkeit prüfen / check dependency
if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo "PyQt6 is missing. Install it with:"
    if command -v pacman >/dev/null; then
        echo "  sudo pacman -S python-pyqt6"
    elif command -v apt-get >/dev/null; then
        echo "  sudo apt install python3-pyqt6"
    elif command -v dnf >/dev/null; then
        echo "  sudo dnf install python3-pyqt6"
    else
        echo "  (install the PyQt6 package for your distribution)"
    fi
    exit 1
fi

mkdir -p "$APP_DIR" "$BIN_DIR" "$(dirname "$DESKTOP_FILE")"
cp "$SRC_DIR/savedesktopdesign.py" "$APP_DIR/"

for launcher in saveyourkdedesign savedesktopdesign; do
cat > "$BIN_DIR/$launcher" <<EOF
#!/usr/bin/env bash
exec python3 "$APP_DIR/savedesktopdesign.py" "\$@"
EOF
chmod +x "$BIN_DIR/$launcher"
done

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=SaveYourKDEDesign
Comment=KDE-Plasma-Design & Paketlisten sichern und wiederherstellen
Exec="$BIN_DIR/saveyourkdedesign"
Icon=preferences-desktop-theme
Terminal=false
Categories=Utility;Settings;
EOF

echo "Installiert! Du findest 'SaveYourKDEDesign' im Anwendungsmenü"
echo "oder startest sie mit: saveyourkdedesign (alter Alias: savedesktopdesign)"
