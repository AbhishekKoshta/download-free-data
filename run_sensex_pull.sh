#!/bin/bash
# Runs standalone (no Claude Code / no network call to any LLM) - plain python +
# bash, triggered by a macOS launchd job (see setup_scheduler.sh). Pulls the
# SENSEX expiry-day CAS data, then builds the ATM CE/PE + index collage.
set -uo pipefail

DIR="/Users/abhishekkoshta/Trading/download free data"
PY="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
LOG="$DIR/logs/sensex_pull.log"
mkdir -p "$DIR/logs"

cd "$DIR" || exit 1
{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') run_sensex_pull ====="
  OUT="$("$PY" fetch_sensex_expiry_cas.py 2>&1)"
  echo "$OUT"
  FOLDER="$(echo "$OUT" | grep '^FOLDER=' | cut -d= -f2-)"
  if [ -n "$FOLDER" ]; then
    "$PY" collage_atm_cas.py "$(basename "$FOLDER")" 2>&1
  elif echo "$OUT" | grep -q '^SKIP:'; then
    echo "not an expiry day - skipped cleanly, nothing to collage"
  else
    echo "no FOLDER= line found - fetch failed, skipping collage"
  fi
  echo "===== done ====="
} >> "$LOG" 2>&1
