# download-free-data

Free-API data pullers for the CAS (Closing Auction Session) expiry-day research
in `~/Trading` (NIFTY/SENSEX index-freeze hypothesis — see the main workspace's
`CLAUDE.md`). Every weekly expiry, this pulls the full trading day (09:15-15:40
IST) of 1-min candles for the index and its ATM +/- a few strikes, from Upstox's
free no-auth public API.

## Files

- `cas_expiry_common.py` — shared puller logic (instrument master lookup,
  1-min candle fetch, CSV writer).
- `fetch_nifty_expiry_cas.py` / `fetch_sensex_expiry_cas.py` — per-exchange config
  (NSE/Upstox `NIFTY`, BSE/Upstox `SENSEX`).
- `collage_atm_cas.py` — builds a 3-panel (index/ATM CE/ATM PE) 15:00-15:30
  candlestick collage PNG from a fetched folder.
- `run_nifty_pull.sh` / `run_sensex_pull.sh` — local launchd wrapper scripts
  (macOS only; see `~/Library/LaunchAgents/com.abhishekkoshta.*-expiry-pull.plist`).
- `<expiry_date>_<SYMBOL>/` — one folder per expiry actually pulled, containing
  the index CSV, one CSV per ATM+/-band option instrument, `atm_strike.txt`,
  and the collage PNG.

## Scheduling — and why it's weekday-agnostic

Both the GitHub Actions workflows (`.github/workflows/fetch-nifty-expiry.yml`,
`fetch-sensex-expiry.yml`) and the local launchd jobs run **every weekday**
after close, not just "Tuesday" / "Thursday". The puller itself decides
whether there's anything to do: it asks Upstox's *live* instrument master
whether today is a listed expiry, and no-ops cleanly (prints `SKIP: ...`,
exit 0) if not.

This is deliberate, to survive two real-world edge cases without a code
change:

- **A holiday falls on the usual expiry day** — the exchange shifts that
  week's expiry to the previous trading day (T-1). Since the master reflects
  the *actual* listed expiry date, running daily catches whichever day that
  turns out to be.
- **SEBI changes the weekly expiry weekday** (it has done this before — NSE
  and BSE currently run Tuesday/Thursday respectively, per the config
  comments, but that's a label, not logic the scripts rely on). Nothing here
  hardcodes a weekday; the schedule just needs to run often enough to catch
  whatever day the exchange announces.

If you ever see repeated `SKIP:` runs where you expected data, check the
`next listed expiry` the script prints — if it's not what you expect, the
exchange has moved something and the workflow will just start firing on the
new day automatically.

## Known limitation

Upstox's free API only serves *currently listed* contracts. Once a weekly
expiry passes, it drops out of the master and its 1-min history isn't
reachable without an authenticated "expired instruments" call (OAuth, not
set up here). So each symbol's puller must run **on its own expiry day**,
shortly after close and before the next day's rollover — which is exactly
what the daily-check schedule above guarantees.

## Setup

```bash
pip install -r requirements.txt
python3 fetch_nifty_expiry_cas.py     # or fetch_sensex_expiry_cas.py
```

For a specific already-listed expiry: `python3 fetch_nifty_expiry_cas.py 2026-09-22`.
