"""1-min candlestick collages for the plain daily archive: SENSEX/NIFTY index
+ ATM CE + ATM PE. Writes TWO PNGs per run - the full session (09:15-15:30)
and a zoomed last-hour view (14:30-15:30). A CAS freeze marker is drawn
automatically whenever one is actually present in that day's data (detected
straight from the index - see collage_atm_cas.detect_freeze_hhmm). This
isn't limited to that symbol's own expiry day: observed 2026-09-17, NIFTY's
index froze (~15:15-15:27) on a day only SENSEX expired, so the freeze looks
like a general closing-auction-style mechanism, not an expiry-only one.
Reads the 1min_download/<date>_<SYMBOL> folders that
fetch_{nifty,sensex}_daily_1min.py already wrote.

Usage:
    python3 collage_daily_1min.py "1min_download/2026-09-17_SENSEX"          # ATM read from atm_strike.txt
    python3 collage_daily_1min.py "1min_download/2026-09-17_SENSEX" 74400    # explicit ATM strike

The folder argument can also be an absolute path (the runner scripts pass the
FOLDER= line printed by fetch_{nifty,sensex}_daily_1min.py directly).
"""
from __future__ import annotations
import os
import sys

from collage_atm_cas import build_collage, _resolve_folder_atm

FULL_WINDOW = ("09:15", "15:30")
LAST_HOUR_WINDOW = ("14:30", "15:30")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 collage_daily_1min.py <1min_download_folder> [atm_strike]")
    folder = sys.argv[1]
    base, symbol, atm = _resolve_folder_atm(folder)
    date_label = os.path.basename(base).split("_")[0]  # base is .../<date>_<SYMBOL>

    for (win_start, win_end), suffix in (
        (FULL_WINDOW, "fullday"),
        (LAST_HOUR_WINDOW, "lasthour"),
    ):
        out_path = build_collage(
            base, symbol, atm,
            suptitle=f"{symbol} daily {date_label} - ATM {atm} - {win_start}-{win_end} (1-min)",
            win_start=win_start, win_end=win_end,
            out_name=f"collage_ATM{atm}_{suffix}.png",
        )
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
