#!/bin/bash
# Runs standalone (no Claude Code / no network call to any LLM) - plain python +
# bash, triggered by a macOS launchd job (see setup_scheduler.sh). Pulls the
# NIFTY expiry-day CAS data (expiry_data/, builds the ATM CE/PE + index
# collage), then separately pulls the daily front-week 1-min option-chain
# archive (1min_download/) - that one runs every trading day, not just expiry.
set -uo pipefail

DIR="/Users/abhishekkoshta/Trading/download free data"
PY="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
LOG="$DIR/logs/nifty_pull.log"
mkdir -p "$DIR/logs"

cd "$DIR" || exit 1
{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') run_nifty_pull ====="
  OUT="$("$PY" fetch_nifty_expiry_cas.py 2>&1)"
  echo "$OUT"
  FOLDER="$(echo "$OUT" | grep '^FOLDER=' | cut -d= -f2-)"
  if [ -n "$FOLDER" ]; then
    COLLAGE_OUT="$("$PY" collage_atm_cas.py "expiry_data/$(basename "$FOLDER")" 2>&1)"
    echo "$COLLAGE_OUT"
    COLLAGE_PNG="$(echo "$COLLAGE_OUT" | grep '^Wrote ' | sed 's/^Wrote //')"
    # Open the finished collage so a real run is visually obvious, not just a
    # log line - this only makes sense for a local/GUI session (launchd or a
    # manual run), never in GitHub Actions' headless runner.
    [ -n "$COLLAGE_PNG" ] && open "$COLLAGE_PNG" 2>&1
  elif echo "$OUT" | grep -q '^SKIP:'; then
    echo "not an expiry day - skipped cleanly, nothing to collage"
  else
    echo "no FOLDER= line found - fetch failed, skipping collage"
  fi

  echo "----- daily 1-min archive -----"
  "$PY" fetch_nifty_daily_1min.py 2>&1
  echo "===== done ====="
} >> "$LOG" 2>&1
