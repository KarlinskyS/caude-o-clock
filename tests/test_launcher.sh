#!/bin/bash
# Smoke test for `caude start` without touching the user's real launchd jobs.

set -euo pipefail

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/caude-launcher-test.XXXXXX")"

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

mkdir -p "$TEMP_DIR/project/.venv/bin" "$TEMP_DIR/bin" "$TEMP_DIR/home"
cp "$PROJECT_ROOT/caude" "$TEMP_DIR/project/caude"
touch "$TEMP_DIR/project/ccusagebar.py"

printf '%s\n' '#!/bin/bash' 'exit 0' > "$TEMP_DIR/project/.venv/bin/python"
printf '%s\n' '#!/bin/bash' 'exit 0' > "$TEMP_DIR/bin/launchctl"
printf '%s\n' \
    '#!/bin/bash' \
    'marker="$CAUDE_TEST_DIR/pgrep-called"' \
    'if [[ -e "$marker" ]]; then exit 0; fi' \
    'touch "$marker"' \
    'exit 1' > "$TEMP_DIR/bin/pgrep"
printf '%s\n' '#!/bin/bash' 'exit 0' > "$TEMP_DIR/bin/plutil"
chmod 0755 "$TEMP_DIR/project/caude" "$TEMP_DIR/project/.venv/bin/python" "$TEMP_DIR/bin/launchctl" "$TEMP_DIR/bin/pgrep" "$TEMP_DIR/bin/plutil"

CAUDE_TEST_DIR="$TEMP_DIR" HOME="$TEMP_DIR/home" PATH="$TEMP_DIR/bin:/usr/bin:/bin" \
    "$TEMP_DIR/project/caude" start > "$TEMP_DIR/output.txt"

grep -F "Caude o'clock v0.2.3" "$TEMP_DIR/output.txt" >/dev/null
grep -F "Happy development!" "$TEMP_DIR/output.txt" >/dev/null
grep -F "com.karlinskys.caude-oc" "$TEMP_DIR/home/Library/LaunchAgents/com.karlinskys.caude-oc.plist" >/dev/null
LAUNCHER_PATH="$(cd "$TEMP_DIR/project" && pwd -P)/caude"
grep -F "$LAUNCHER_PATH" "$TEMP_DIR/home/Library/LaunchAgents/com.karlinskys.caude-oc.plist" >/dev/null

printf 'launcher smoke test passed\n'
