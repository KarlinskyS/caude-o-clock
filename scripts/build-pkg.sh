#!/bin/bash
# Build an unsigned macOS installer package for a tagged release.
# Signing/notarization is intentionally not performed: this project does not
# currently have an Apple Developer ID.  README.md explains the resulting
# Gatekeeper confirmation users will see.

set -euo pipefail

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly VERSION="${1:?Usage: scripts/build-pkg.sh VERSION}"
readonly OUTPUT_DIR="$PROJECT_ROOT/release"
readonly OUTPUT_PATH="$OUTPUT_DIR/Caude-o-clock.pkg"
readonly TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/caude-o-clock-pkg.XXXXXX")"

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

case "$VERSION" in
    *[!0-9A-Za-z.-]*|'')
        printf 'Invalid package version: %s\n' "$VERSION" >&2
        exit 1
        ;;
esac

[[ "$(uname -s)" == "Darwin" ]] || {
    printf 'This package must be built on macOS.\n' >&2
    exit 1
}

mkdir -p "$OUTPUT_DIR"
[[ ! -e "$OUTPUT_PATH" ]] || {
    printf 'Refusing to overwrite %s\n' "$OUTPUT_PATH" >&2
    exit 1
}

SWIFTC="/usr/bin/swiftc"
[[ -x "$SWIFTC" ]] || {
    printf 'Xcode Command Line Tools are required to build the package.\n' >&2
    exit 1
}

APP_SOURCE="$TEMP_DIR/Caude o'clock.app"
mkdir -p "$APP_SOURCE/Contents/MacOS" "$APP_SOURCE/Contents/Resources"
"$SWIFTC" "$PROJECT_ROOT/native/CaudeOClock.swift" \
    -framework AppKit \
    -framework Foundation \
    -o "$APP_SOURCE/Contents/MacOS/Caude o'clock"
install -m 0644 "$PROJECT_ROOT/native/Info.plist" "$APP_SOURCE/Contents/Info.plist"
install -m 0644 "$PROJECT_ROOT/assets/app-icon.icns" "$APP_SOURCE/Contents/Resources/app-icon.icns"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$APP_SOURCE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$APP_SOURCE/Contents/Info.plist"
plutil -lint "$APP_SOURCE/Contents/Info.plist" >/dev/null

PAYLOAD="$TEMP_DIR/payload"
mkdir -p "$PAYLOAD/Applications" "$PAYLOAD/usr/local/bin" "$PAYLOAD/usr/local/lib/caude-o-clock"
ditto "$APP_SOURCE" "$PAYLOAD/Applications/Caude o'clock.app"
install -m 0755 "$PROJECT_ROOT/caude" "$PAYLOAD/usr/local/lib/caude-o-clock/caude"
printf '%s\n' \
    '#!/bin/bash' \
    'exec /usr/local/lib/caude-o-clock/caude "$@"' > "$PAYLOAD/usr/local/bin/caude"
chmod 0755 "$PAYLOAD/usr/local/bin/caude"

pkgbuild \
    --root "$PAYLOAD" \
    --scripts "$PROJECT_ROOT/scripts/pkg" \
    --identifier "com.karlinskys.caude-oc" \
    --version "$VERSION" \
    --install-location / \
    "$OUTPUT_PATH"

printf 'Created unsigned package: %s\n' "$OUTPUT_PATH"
