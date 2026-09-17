#!/bin/bash
# Install/uninstall/check the macOS launchd jobs that auto-run the SENSEX and
# NIFTY expiry-day CAS pulls, Mon-Fri at 15:45 local time - well after the
# ~15:39 CAS-extended options close observed on 17-Sep-2026. Each puller
# checks Upstox's live instrument master and no-ops on non-expiry days, so
# running daily (not just Thursday/Tuesday) survives a holiday shifting that
# week's expiry or SEBI changing the expiry weekday - no edits needed here.
#
# This is plain launchd (macOS's native cron-equivalent) - it runs
# run_sensex_pull.sh / run_nifty_pull.sh directly with bash + python3. No
# Claude Code, no network call to any LLM, nothing but the OS scheduler.
#
# Usage:
#   ./setup_scheduler.sh install     # load both jobs (persists across reboots/logins)
#   ./setup_scheduler.sh uninstall   # unload + remove both jobs
#   ./setup_scheduler.sh status      # show whether they're loaded
#   ./setup_scheduler.sh run-now     # trigger both immediately (for testing)
set -euo pipefail

AGENTS_DIR="$HOME/Library/LaunchAgents"
SENSEX_PLIST="$AGENTS_DIR/com.abhishekkoshta.sensex-expiry-pull.plist"
NIFTY_PLIST="$AGENTS_DIR/com.abhishekkoshta.nifty-expiry-pull.plist"
SENSEX_LABEL="com.abhishekkoshta.sensex-expiry-pull"
NIFTY_LABEL="com.abhishekkoshta.nifty-expiry-pull"

case "${1:-}" in
  install)
    launchctl load -w "$SENSEX_PLIST"
    launchctl load -w "$NIFTY_PLIST"
    echo "Installed. They'll fire every weekday at 15:45 local time (no-op on non-expiry days) even with no Claude session running."
    ;;
  uninstall)
    launchctl unload "$SENSEX_PLIST" 2>/dev/null || true
    launchctl unload "$NIFTY_PLIST" 2>/dev/null || true
    echo "Unloaded. (plist files left on disk in $AGENTS_DIR - delete them too if you want them fully gone.)"
    ;;
  status)
    launchctl list | grep -i abhishekkoshta || echo "(none loaded)"
    ;;
  run-now)
    launchctl start "$SENSEX_LABEL"
    launchctl start "$NIFTY_LABEL"
    echo "Triggered both immediately - check logs/sensex_pull.log and logs/nifty_pull.log"
    ;;
  *)
    echo "Usage: $0 {install|uninstall|status|run-now}"
    exit 1
    ;;
esac
