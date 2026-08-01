# Caude o'clock

A macOS menu bar app that shows your Claude 5-hour / weekly usage windows,
notifies you at 50/75/90% and when the 5-hour limit resets, and shows
today's local message/token counts pulled from Claude Code's own session
logs. Built from scratch on PyObjC/AppKit (no third-party menu bar toolkit).

It reuses the OAuth token Claude Code's CLI already stores in the macOS
Keychain (after you run `claude login`) — no browser cookies, no separate
login flow.

## Requirements

- macOS
- Python 3
- Claude Code CLI installed and logged in at least once (`claude login`)

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python ccusagebar.py
```

A ghost-with-a-pocket-watch icon and a percentage (`NN%`) appear in the
menu bar. Click it for the usage card; click elsewhere to dismiss.

## Run at login (launchd)

Create `~/Library/LaunchAgents/com.yourname.ccusagebar.plist`, substituting
your own paths:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yourname.ccusagebar</string>
    <key>ProgramArguments</key>
    <array>
        <string>/absolute/path/to/caude-o-clock/.venv/bin/python</string>
        <string>/absolute/path/to/caude-o-clock/ccusagebar.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/absolute/path/to/caude-o-clock</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>/absolute/path/to/caude-o-clock/ccusagebar.log</string>
    <key>StandardErrorPath</key>
    <string>/absolute/path/to/caude-o-clock/ccusagebar.err.log</string>
</dict>
</plist>
```

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yourname.ccusagebar.plist
```

## Notes / caveats

- Uses `https://api.anthropic.com/api/oauth/usage`, which is **not a
  documented or officially supported** endpoint — it's the same one
  claude.ai's own settings page calls internally, and it enforces its own
  (undocumented) rate limit unrelated to your actual Claude usage. The app
  polls gently (every 5 minutes, no fetch on popover open) and backs off on
  `Retry-After` when rate-limited, but the endpoint could change without
  notice.
- Localized into English, Russian, Spanish, German, French, Portuguese,
  Japanese, and Chinese — picked automatically from macOS's own ordered
  language preferences (System Settings → General → Language & Region).
  Override for testing: `CCUSAGE_LANG=ja ./.venv/bin/python ccusagebar.py`.
