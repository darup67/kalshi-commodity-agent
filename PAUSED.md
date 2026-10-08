# PAUSED October 8, 2026 (user request: "pause the kalshi 15m agents and all associated routines")
The Kalshi gold/WTI 15-minute caller and its weekly recalibration job are unloaded; plists renamed to .plist.disabled. The watchdog skips it while this file exists.
Resume: for l in kalshicommodity kalshicommodity.recal; do mv ~/Library/LaunchAgents/com.dhruv.$l.plist.disabled ~/Library/LaunchAgents/com.dhruv.$l.plist; launchctl load ~/Library/LaunchAgents/com.dhruv.$l.plist; done; then rm this file.
