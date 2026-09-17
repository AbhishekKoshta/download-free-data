"""Shared puller for index-expiry CAS (Closing Auction Session) data.

Since 3-Aug-2026, index derivatives freeze the underlying index print at ~15:14
(last traded price carried flat to close) while options keep trading into the
close. Hypothesis under test: the color of the 15:27 1-min candle predicts a
post-freeze CE/PE move. `run()` pulls, for one expiry day, the FULL trading day
(09:15-15:40 IST) of:
  - the INDEX 1-min candles (shows the ~15:14 freeze)
  - the OPTION CHAIN 1-min candles for strikes within +/- STRIKE_BAND points of
    the freeze/close (CE+PE), one file per instrument

Uses Upstox's free no-auth public APIs (instrument master + historical/intraday
candle). IMPORTANT LIMITATION: Upstox's free master + candle API only serves
contracts still listed (expiry >= today). Once a weekly expiry passes, it drops
out of the master and its 1-min history is no longer reachable without an
authenticated Upstox "expired instruments" API call (needs an OAuth access
token, not set up in this workspace). So this only works for TODAY's (or a
future) expiry, run shortly after that expiry's close, before the contract
drops out of the master.
"""
from __future__ import annotations
import gzip
import json
import os
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests

IST = timezone(timedelta(hours=5, minutes=30))
HDRS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "application/json"}
SESSION = requests.Session()
SESSION.headers.update(HDRS)

WINDOW_START = (9, 15)      # market open
WINDOW_END = (15, 40)       # past the CAS-extended options close
FREEZE_HHMM = "15:14"       # index print freezes at/after this time (SENSEX-observed; assumed same for NIFTY)
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class SymbolConfig:
    label: str            # "SENSEX" / "NIFTY" - used as folder suffix + filename prefix
    master_url: str        # Upstox exchange instrument-master (.json.gz) URL
    option_name: str       # "name" field to match in the master for this underlying's options
    index_key: str          # instrument_key for the underlying index (spot) candles
    strike_step: int
    strike_band: int        # +/- this many points around ATM


def load_master(master_url: str) -> list:
    r = SESSION.get(master_url, timeout=30)
    r.raise_for_status()
    return json.loads(gzip.decompress(r.content))


def fetch_1m(instrument_key: str, day: date) -> list:
    keyq = urllib.parse.quote(instrument_key, safe="")
    today = datetime.now(IST).date()
    if day >= today:
        url = f"https://api.upstox.com/v3/historical-candle/intraday/{keyq}/minutes/1"
    else:
        url = (f"https://api.upstox.com/v3/historical-candle/{keyq}/minutes/1/"
               f"{day.isoformat()}/{day.isoformat()}")
    r = SESSION.get(url, timeout=25)
    r.raise_for_status()
    return (r.json().get("data") or {}).get("candles") or []


def window_filter(candles: list, day: date) -> list:
    frm = datetime(day.year, day.month, day.day, *WINDOW_START, tzinfo=IST)
    to = datetime(day.year, day.month, day.day, *WINDOW_END, tzinfo=IST)
    return [c for c in candles if frm <= datetime.fromisoformat(c[0]) <= to]


def candles_to_df(candles: list, extra: dict) -> pd.DataFrame:
    rows = []
    for c in candles:
        ts, o, h, l, cl, vol, oi = (list(c) + [None] * 7)[:7]
        row = {"datetime": ts, "open": o, "high": h, "low": l, "close": cl,
               "volume": vol, "oi": oi}
        row.update(extra)
        rows.append(row)
    return pd.DataFrame(rows)


def run(cfg: SymbolConfig, expiry_arg: str | None) -> None:
    master = load_master(cfg.master_url)
    opts = [d for d in master if d.get("name") == cfg.option_name
            and d.get("instrument_type") in ("CE", "PE")]
    if not opts:
        raise SystemExit(f"No {cfg.option_name} options found in the Upstox master")

    listed_expiries = sorted({d["expiry"] for d in opts})
    listed_dates = {datetime.fromtimestamp(e / 1000, IST).date(): e for e in listed_expiries}

    if expiry_arg:
        expiry_date = date.fromisoformat(expiry_arg)
        if expiry_date not in listed_dates:
            raise SystemExit(f"{expiry_date} not in Upstox's currently-listed {cfg.label} expiries: "
                              f"{sorted(listed_dates)}. Past expiries are no longer reachable "
                              "via the free API - see this module's docstring.")
    else:
        # No hardcoded weekday here on purpose: the exchange is the source of
        # truth for which date actually expires (SEBI can change the weekly
        # expiry weekday, and a holiday on the usual day shifts that week's
        # expiry to the previous trading day). We only fetch when TODAY is
        # itself a listed expiry - this lets a daily cron/launchd run safely
        # every weekday and self-adjust to either kind of change with no code
        # edits, instead of guessing "today + N days" against a fixed weekday.
        today = datetime.now(IST).date()
        if today not in listed_dates:
            upcoming = min((d for d in listed_dates if d >= today), default=None)
            print(f"SKIP: {today} is not a listed {cfg.label} expiry "
                  f"(next listed expiry: {upcoming}) - nothing to do today")
            return
        expiry_date = today
    exp_ms = listed_dates[expiry_date]
    print(f"{cfg.label} expiry: {expiry_date}")

    day_dir = os.path.join(OUT_DIR, f"{expiry_date}_{cfg.label}")
    os.makedirs(day_dir, exist_ok=True)

    # 1) index candles for the window (shows the ~15:14 CAS freeze)
    idx_candles = window_filter(fetch_1m(cfg.index_key, expiry_date), expiry_date)
    if not idx_candles:
        raise SystemExit(f"No {cfg.label} index candles in {WINDOW_START}-{WINDOW_END} for {expiry_date} "
                          "(day not yet traded, or too far in the past for the intraday endpoint)")
    idx_df = candles_to_df(idx_candles, {"symbol": f"{cfg.label}_INDEX"})
    idx_df["datetime"] = pd.to_datetime(idx_df["datetime"])
    idx_df = idx_df.sort_values("datetime").reset_index(drop=True)

    # reference close = last index print at/after the freeze time (the frozen settlement-basis price)
    freeze_row = idx_df[idx_df["datetime"].dt.strftime("%H:%M") >= FREEZE_HHMM]
    ref_close = float((freeze_row.iloc[0]["close"] if not freeze_row.empty else idx_df.iloc[-1]["close"]))
    print(f"Reference (freeze) close: {ref_close}")

    idx_csv = os.path.join(day_dir, f"{cfg.label.lower()}_index_1m.csv")
    idx_df.to_csv(idx_csv, index=False)
    print(f"Wrote {len(idx_df)} index rows -> {idx_csv}")

    # 2) option chain, ATM +/- strike_band, same window - one file per instrument
    atm = round(ref_close / cfg.strike_step) * cfg.strike_step
    n_steps = cfg.strike_band // cfg.strike_step
    wanted_strikes = {atm + k * cfg.strike_step for k in range(-n_steps, n_steps + 1)}

    chain = [d for d in opts if d["expiry"] == exp_ms and d["strike_price"] in wanted_strikes]
    chain.sort(key=lambda d: (d["strike_price"], d["instrument_type"]))
    print(f"Option instruments: {len(chain)} (strikes {min(wanted_strikes):.0f}-{max(wanted_strikes):.0f})")

    written = 0
    for d in chain:
        try:
            candles = window_filter(fetch_1m(d["instrument_key"], expiry_date), expiry_date)
        except Exception as e:
            print(f"  ! {d['trading_symbol']}: {e}")
            continue
        if not candles:
            print(f"  ! {d['trading_symbol']}: no candles")
            continue
        extra = {"tradingsymbol": d["trading_symbol"], "strike": d["strike_price"],
                  "type": d["instrument_type"], "expiry": str(expiry_date)}
        df = candles_to_df(candles, extra)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime").reset_index(drop=True)

        fname = f"{cfg.label}_{int(d['strike_price'])}_{d['instrument_type']}.csv"
        df.to_csv(os.path.join(day_dir, fname), index=False)
        written += 1
        print(f"  wrote {len(df)} rows -> {fname}")

    if not written:
        raise SystemExit("No option candle data returned for this window")
    print(f"Wrote {written} option files -> {day_dir}")

    with open(os.path.join(day_dir, "atm_strike.txt"), "w") as f:
        f.write(str(int(atm)))

    # last line, machine-readable: the runner script/cron job greps this to
    # chain into the collage step without any human (or Claude) in the loop.
    print(f"FOLDER={day_dir}")


def main_cli(cfg: SymbolConfig) -> None:
    expiry_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(cfg, expiry_arg)
