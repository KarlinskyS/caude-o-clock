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

BUILD_VENV="$TEMP_DIR/build-venv"
BUILD_PYTHON="$(command -v python3.12 || command -v python3 || true)"
[[ -n "$BUILD_PYTHON" ]] || {
    printf 'Python 3.12 or later is required to build the package.\n' >&2
    exit 1
}
"$BUILD_PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 12))' || {
    printf 'Python 3.12 or later is required to build the package.\n' >&2
    exit 1
}
"$BUILD_PYTHON" -m venv "$BUILD_VENV"
"$BUILD_VENV/bin/python" -m pip install --disable-pip-version-check --quiet -r "$PROJECT_ROOT/requirements-build.txt"

PY2APP_LOG="$TEMP_DIR/py2app.log"
if ! "$BUILD_VENV/bin/python" "$PROJECT_ROOT/setup.py" -q py2app \
    --dist-dir "$TEMP_DIR/dist" \
    --bdist-base "$TEMP_DIR/build" > "$PY2APP_LOG" 2>&1; then
    tail -n 80 "$PY2APP_LOG" >&2
    exit 1
fi

APP_SOURCE="$TEMP_DIR/dist/Caude o'clock.app"
[[ -d "$APP_SOURCE" ]] || {
    printf 'py2app did not produce Caude o\047clock.app\n' >&2
    exit 1
}

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
