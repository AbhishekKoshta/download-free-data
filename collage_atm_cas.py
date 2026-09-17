"""1-min candlestick collage: SENSEX/NIFTY index + ATM CE + ATM PE, 15:00-15:30,
for the CAS-freeze / 15:27-candle hypothesis. Reads the expiry_data/<date>/<SYMBOL>
folders that fetch_sensex_expiry_cas.py / fetch_nifty_expiry_cas.py already wrote.

Usage:
    python3 collage_atm_cas.py "expiry_data/2026-09-17/SENSEX"          # ATM read from atm_strike.txt
    python3 collage_atm_cas.py "expiry_data/2026-09-17/SENSEX" 74400    # explicit ATM strike

The folder argument can also be an absolute path (the runner scripts pass the
FOLDER= line printed by the fetch scripts directly).

`build_collage()` is shared with collage_daily_1min.py, which draws the same
3-panel chart for the plain (no CAS-freeze) 1min_download/ archive.
"""
from __future__ import annotations
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd

UP, DOWN = "#26a69a", "#ef5350"     # same up/down pair as trade_snapshots.py (CVD-validated)
HYPOTHESIS_HHMM = "15:27"
MIN_FREEZE_RUN = 3      # consecutive identical index closes to call it a freeze, not noise
WIN_START, WIN_END = "15:00", "15:30"


def load(path: str, win_start: str, win_end: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    hhmm = df["datetime"].dt.strftime("%H:%M")
    return df[(hhmm >= win_start) & (hhmm <= win_end)].reset_index(drop=True)


def detect_freeze_hhmm(idx_df: pd.DataFrame, min_run: int = MIN_FREEZE_RUN) -> str | None:
    """Find the CAS freeze directly in the data (the exchange prints a flat
    line from ~15:14 to just before close on an actual expiry day) instead of
    assuming a fixed clock time: scan for the first run of >= min_run
    consecutive identical index closes and return that run's HH:MM. Returns
    None on an ordinary trading day, where the index just keeps moving."""
    closes = idx_df["close"].tolist()
    hhmm = idx_df["datetime"].dt.strftime("%H:%M").tolist()
    i, n = 0, len(closes)
    while i < n:
        j = i
        while j + 1 < n and closes[j + 1] == closes[i]:
            j += 1
        if j - i + 1 >= min_run:
            return hhmm[i]
        i = j + 1
    return None


def draw_candles(ax, df: pd.DataFrame, title: str, freeze_hhmm: str | None = None):
    for i, r in df.iterrows():
        up = r["close"] >= r["open"]
        col = UP if up else DOWN
        ax.plot([i, i], [r["low"], r["high"]], color=col, lw=0.9, zorder=2)
        body = max(abs(r["close"] - r["open"]), (df["high"].max() - df["low"].min()) * 0.002)
        ax.add_patch(Rectangle((i - 0.3, min(r["open"], r["close"])), 0.6, body,
                                facecolor=col, edgecolor=col, zorder=3))

    hhmm = df["datetime"].dt.strftime("%H:%M")
    if freeze_hhmm is not None:
        freeze_idx = hhmm[hhmm == freeze_hhmm].index
        hyp_idx = hhmm[hhmm == HYPOTHESIS_HHMM].index
        if len(freeze_idx):
            ax.axvline(freeze_idx[0], color="#898781", lw=1.1, ls="--", zorder=1)
            ax.text(freeze_idx[0], ax.get_ylim()[1] if ax.get_ylim()[1] else df["high"].max(),
                    f" {freeze_hhmm} freeze", color="#52514e", fontsize=7, va="top", rotation=90)
        if len(hyp_idx):
            ax.axvspan(hyp_idx[0] - 0.5, hyp_idx[0] + 0.5, color="#eda100", alpha=0.15, zorder=0)

    step = max(1, len(df) // 10)
    ax.set_xticks(range(0, len(df), step))
    ax.set_xticklabels(hhmm.iloc[::step], rotation=45, ha="right", fontsize=7, color="#52514e")
    ax.set_title(title, fontsize=10, color="#0b0b0b", loc="left")
    ax.tick_params(axis="y", labelsize=7, colors="#52514e")
    ax.grid(axis="y", color="#e1e0d9", lw=0.6, zorder=0)
    for spine in ax.spines.values():
        spine.set_color("#c3c2b7")


def build_collage(base: str, symbol: str, atm: str, suptitle: str,
                   win_start: str, win_end: str, out_name: str) -> str:
    idx_path = os.path.join(base, f"{symbol.lower()}_index_1m.csv")
    ce_path = os.path.join(base, f"{symbol}_{atm}_CE.csv")
    pe_path = os.path.join(base, f"{symbol}_{atm}_PE.csv")

    idx_df = load(idx_path, win_start, win_end)
    ce_df = load(ce_path, win_start, win_end)
    pe_df = load(pe_path, win_start, win_end)

    # Detected once from the index, then applied to all three panels so the
    # CE/PE charts also show where the underlying stopped moving - shows up
    # on an actual expiry day (any collage, expiry_data/ or 1min_download/)
    # and stays off on an ordinary trading day, with no hardcoded clock time.
    freeze_hhmm = detect_freeze_hhmm(idx_df)

    fig, axes = plt.subplots(3, 1, figsize=(11, 10), facecolor="#fcfcfb")
    fig.suptitle(suptitle, fontsize=13, color="#0b0b0b")
    draw_candles(axes[0], idx_df, f"{symbol} index", freeze_hhmm)
    draw_candles(axes[1], ce_df, f"{atm} CE", freeze_hhmm)
    draw_candles(axes[2], pe_df, f"{atm} PE", freeze_hhmm)
    for ax in axes:
        ax.set_facecolor("#fcfcfb")

    fig.legend(handles=[Rectangle((0, 0), 1, 1, facecolor=UP, edgecolor=UP),
                         Rectangle((0, 0), 1, 1, facecolor=DOWN, edgecolor=DOWN)],
                labels=["up candle", "down candle"], loc="upper right", fontsize=8, frameon=False)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_path = os.path.join(base, out_name)
    fig.savefig(out_path, dpi=160)
    return out_path


def _resolve_folder_atm(folder: str) -> tuple[str, str, str]:
    """Shared CLI arg handling: returns (base_dir, symbol, atm)."""
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder)
    if len(sys.argv) > 2:
        atm = sys.argv[2]
    else:
        atm_path = os.path.join(base, "atm_strike.txt")
        if not os.path.exists(atm_path):
            raise SystemExit(f"No atm_strike.txt in {base} and no strike given on the command line")
        atm = open(atm_path).read().strip()
    symbol = "SENSEX" if "SENSEX" in folder.upper() else "NIFTY"
    return base, symbol, atm


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 collage_atm_cas.py <expiry_folder> [atm_strike]")
    folder = sys.argv[1]
    base, symbol, atm = _resolve_folder_atm(folder)
    date_label = os.path.basename(os.path.dirname(base))  # base is .../<date>/<SYMBOL>

    out_path = build_collage(
        base, symbol, atm,
        suptitle=f"{symbol} expiry {date_label} - ATM {atm} - {WIN_START}-{WIN_END} (1-min)",
        win_start=WIN_START, win_end=WIN_END,
        out_name=f"collage_ATM{atm}_1500_1530.png",
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
