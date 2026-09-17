"""Full-day 1-min candlestick collage: SENSEX/NIFTY index + ATM CE + ATM PE,
09:15-15:30, for the plain daily archive (no CAS freeze - that only happens
on an actual expiry day, see collage_atm_cas.py for that variant). Reads the
1min_download/<date>_<SYMBOL> folders that fetch_{nifty,sensex}_daily_1min.py
already wrote.

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

WIN_START, WIN_END = "09:15", "15:30"


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 collage_daily_1min.py <1min_download_folder> [atm_strike]")
    folder = sys.argv[1]
    base, symbol, atm = _resolve_folder_atm(folder)
    date_label = os.path.basename(base).split("_")[0]  # base is .../<date>_<SYMBOL>

    out_path = build_collage(
        base, symbol, atm,
        suptitle=f"{symbol} daily {date_label} - ATM {atm} - {WIN_START}-{WIN_END} (1-min)",
        win_start=WIN_START, win_end=WIN_END,
        out_name=f"collage_ATM{atm}_fullday.png",
        show_freeze_markers=False,
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
