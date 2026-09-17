"""1-min candlestick collage: SENSEX/NIFTY index + ATM CE + ATM PE, 15:00-15:30,
for the CAS-freeze / 15:27-candle hypothesis. Reads the per-expiry folders that
fetch_sensex_expiry_cas.py / fetch_nifty_expiry_cas.py already wrote.

Usage:
    python3 collage_atm_cas.py "2026-09-17_SENSEX"            # ATM read from atm_strike.txt
    python3 collage_atm_cas.py "2026-09-17_SENSEX" 74400       # explicit ATM strike
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
FREEZE_HHMM = "15:14"
HYPOTHESIS_HHMM = "15:27"
WIN_START, WIN_END = "15:00", "15:30"


def load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    hhmm = df["datetime"].dt.strftime("%H:%M")
    return df[(hhmm >= WIN_START) & (hhmm <= WIN_END)].reset_index(drop=True)


def draw_candles(ax, df: pd.DataFrame, title: str):
    for i, r in df.iterrows():
        up = r["close"] >= r["open"]
        col = UP if up else DOWN
        ax.plot([i, i], [r["low"], r["high"]], color=col, lw=0.9, zorder=2)
        body = max(abs(r["close"] - r["open"]), (df["high"].max() - df["low"].min()) * 0.002)
        ax.add_patch(Rectangle((i - 0.3, min(r["open"], r["close"])), 0.6, body,
                                facecolor=col, edgecolor=col, zorder=3))

    hhmm = df["datetime"].dt.strftime("%H:%M")
    freeze_idx = hhmm[hhmm == FREEZE_HHMM].index
    hyp_idx = hhmm[hhmm == HYPOTHESIS_HHMM].index
    if len(freeze_idx):
        ax.axvline(freeze_idx[0], color="#898781", lw=1.1, ls="--", zorder=1)
        ax.text(freeze_idx[0], ax.get_ylim()[1] if ax.get_ylim()[1] else df["high"].max(),
                " 15:14 freeze", color="#52514e", fontsize=7, va="top", rotation=90)
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


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 collage_atm_cas.py <expiry_folder> [atm_strike]")
    folder = sys.argv[1]
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder)

    if len(sys.argv) > 2:
        atm = sys.argv[2]
    else:
        atm_path = os.path.join(base, "atm_strike.txt")
        if not os.path.exists(atm_path):
            raise SystemExit(f"No atm_strike.txt in {base} and no strike given on the command line")
        atm = open(atm_path).read().strip()

    symbol = "SENSEX" if "SENSEX" in folder.upper() else "NIFTY"
    idx_path = os.path.join(base, f"{symbol.lower()}_index_1m.csv")
    ce_path = os.path.join(base, f"{symbol}_{atm}_CE.csv")
    pe_path = os.path.join(base, f"{symbol}_{atm}_PE.csv")

    idx_df, ce_df, pe_df = load(idx_path), load(ce_path), load(pe_path)

    fig, axes = plt.subplots(3, 1, figsize=(11, 10), facecolor="#fcfcfb")
    fig.suptitle(f"{symbol} expiry {folder.split('_')[0]} - ATM {atm} - 15:00-15:30 (1-min)",
                 fontsize=13, color="#0b0b0b")
    draw_candles(axes[0], idx_df, f"{symbol} index")
    draw_candles(axes[1], ce_df, f"{atm} CE")
    draw_candles(axes[2], pe_df, f"{atm} PE")
    for ax in axes:
        ax.set_facecolor("#fcfcfb")

    fig.legend(handles=[Rectangle((0, 0), 1, 1, facecolor=UP, edgecolor=UP),
                         Rectangle((0, 0), 1, 1, facecolor=DOWN, edgecolor=DOWN)],
                labels=["up candle", "down candle"], loc="upper right", fontsize=8, frameon=False)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_path = os.path.join(base, f"collage_ATM{atm}_1500_1530.png")
    fig.savefig(out_path, dpi=160)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
