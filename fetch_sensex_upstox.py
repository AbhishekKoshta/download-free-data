"""SENSEX option-chain 1-min candles for the last 30 minutes, via Upstox's free
no-auth public APIs (instrument master + historical/intraday candle).

Same pattern as Algo_Nifty50/market-analysis/tools/option_pnl_simulator/upstox_data.py
but for BSE_FO (SENSEX) instead of NSE (NIFTY/BANKNIFTY).
"""
from __future__ import annotations
import gzip
import json
import os
import urllib.parse
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

IST = timezone(timedelta(hours=5, minutes=30))
HDRS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "application/json"}
SESSION = requests.Session()
SESSION.headers.update(HDRS)

BSE_MASTER_URL = "https://assets.upstox.com/market-quote/instruments/exchange/BSE.json.gz"
INDEX_KEY = "BSE_INDEX|SENSEX"
STRIKE_STEP = 100
STRIKES_EACH_SIDE = 5
OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sensex_option_chain_1m.csv")


def load_bse_master() -> list:
    r = SESSION.get(BSE_MASTER_URL, timeout=30)
    r.raise_for_status()
    return json.loads(gzip.decompress(r.content))


def latest_spot() -> float:
    keyq = urllib.parse.quote(INDEX_KEY, safe="")
    url = f"https://api.upstox.com/v3/historical-candle/intraday/{keyq}/minutes/1"
    r = SESSION.get(url, timeout=20)
    r.raise_for_status()
    candles = (r.json().get("data") or {}).get("candles") or []
    if not candles:
        raise SystemExit("No intraday SENSEX index candles available")
    return float(candles[0][4])  # most-recent candle's close


def fetch_1m(instrument_key: str, frm: datetime, to: datetime) -> list:
    """1-min candles for instrument_key between frm/to (both IST-aware)."""
    keyq = urllib.parse.quote(instrument_key, safe="")
    today = datetime.now(IST).date()
    if to.date() >= today:
        url = f"https://api.upstox.com/v3/historical-candle/intraday/{keyq}/minutes/1"
    else:
        url = (f"https://api.upstox.com/v3/historical-candle/{keyq}/minutes/1/"
               f"{to.date().isoformat()}/{frm.date().isoformat()}")
    r = SESSION.get(url, timeout=25)
    r.raise_for_status()
    candles = (r.json().get("data") or {}).get("candles") or []
    return [c for c in candles if frm <= datetime.fromisoformat(c[0]) <= to]


def main():
    master = load_bse_master()
    opts = [d for d in master if d.get("name") == "SENSEX" and d.get("instrument_type") in ("CE", "PE")]
    if not opts:
        raise SystemExit("No SENSEX options found in Upstox BSE master")

    today = datetime.now(IST).date()
    exp_ms = sorted({d["expiry"] for d in opts})
    nearest_exp_ms = next(e for e in exp_ms if datetime.fromtimestamp(e / 1000, IST).date() >= today)
    nearest_exp = datetime.fromtimestamp(nearest_exp_ms / 1000, IST).date()
    print(f"Nearest expiry: {nearest_exp}")

    spot = latest_spot()
    print(f"SENSEX last price: {spot}")

    atm = round(spot / STRIKE_STEP) * STRIKE_STEP
    wanted_strikes = {atm + k * STRIKE_STEP for k in range(-STRIKES_EACH_SIDE, STRIKES_EACH_SIDE + 1)}

    chain = [d for d in opts if d["expiry"] == nearest_exp_ms and d["strike_price"] in wanted_strikes]
    chain.sort(key=lambda d: (d["strike_price"], d["instrument_type"]))
    print(f"Instruments in chain: {len(chain)} (strikes {min(wanted_strikes):.0f}-{max(wanted_strikes):.0f})")

    now = datetime.now(IST)
    market_close_today = now.replace(hour=15, minute=30, second=0, microsecond=0)
    to = min(now, market_close_today)
    frm = to - timedelta(minutes=30)
    print(f"Window: {frm} -> {to}")

    rows = []
    for d in chain:
        try:
            candles = fetch_1m(d["instrument_key"], frm, to)
        except Exception as e:
            print(f"  ! {d['trading_symbol']}: {e}")
            continue
        for c in candles:
            ts, o, h, l, cl, vol, oi = c[:7]
            rows.append({
                "tradingsymbol": d["trading_symbol"],
                "strike": d["strike_price"],
                "type": d["instrument_type"],
                "expiry": str(nearest_exp),
                "datetime": ts,
                "open": o, "high": h, "low": l, "close": cl,
                "volume": vol, "oi": oi,
            })

    if not rows:
        raise SystemExit("No candle rows returned for this window")

    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values(["strike", "type", "datetime"]).reset_index(drop=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(df)} rows across {df['tradingsymbol'].nunique()} instruments -> {OUT_CSV}")


if __name__ == "__main__":
    main()
