# download-free-data

Free-API (Upstox, no auth) data pullers for NIFTY/SENSEX 1-min index + option
data, for two purposes that live in two separate folders:

- **`expiry_data/`** — the CAS (Closing Auction Session) expiry-day research
  in `~/Trading` (NIFTY/SENSEX index-freeze hypothesis — see the main
  workspace's `CLAUDE.md`). Only pulled on an actual expiry day.
- **`1min_download/`** — a plain daily archive of the front-week ATM+/-band
  option chain, pulled on **every trading day**, not just expiry. Upstox's
  free API drops a contract the moment it expires, so this is the only way to
  keep that week's intraday option data around for later algo backtesting —
  without it, everything before expiry day itself is lost for good.

Both pull the full trading day (09:15-15:40 IST) of 1-min candles for the
index and its ATM +/- a few strikes.

## Files

- `cas_expiry_common.py` — shared puller logic (instrument master lookup,
  1-min candle fetch, CSV writer) for both `expiry_data/` and `1min_download/`.
- `fetch_nifty_expiry_cas.py` / `fetch_sensex_expiry_cas.py` — expiry-day pull
  (per-exchange config: NSE/Upstox `NIFTY`, BSE/Upstox `SENSEX`) -> `expiry_data/`.
- `fetch_nifty_daily_1min.py` / `fetch_sensex_daily_1min.py` — daily front-week
  pull, same per-exchange config -> `1min_download/`.
- `collage_atm_cas.py` — builds a 3-panel (index/ATM CE/ATM PE) 15:00-15:30
  candlestick collage PNG from a fetched `expiry_data/` folder.
- `run_nifty_pull.sh` / `run_sensex_pull.sh` — local launchd wrapper scripts
  (macOS only; see `~/Library/LaunchAgents/com.abhishekkoshta.*-expiry-pull.plist`).
  Run both the expiry pull (+ collage, opened automatically) and the daily pull.
- `expiry_data/<expiry_date>/<SYMBOL>/` — one folder per expiry actually pulled
  (date first, then symbol nested inside, so a date with both an expiry NIFTY
  and SENSEX would sit side by side), containing the index CSV, one CSV per
  ATM+/-band option instrument, `atm_strike.txt`, and the collage PNG.
- `1min_download/<date>_<SYMBOL>/` — one folder per trading day, containing the
  index CSV, one CSV per ATM+/-band option instrument (of whatever the current
  front-week expiry is), `atm_strike.txt`, and `front_expiry.txt`.

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
set up here). This is exactly why `1min_download/` exists: `expiry_data/`
alone only ever captures the final day of a contract's life, so running the
daily pull too — every trading day, not just expiry — is the only way to
retain that week's earlier intraday option data before it rolls off the
master for good.

## Setup

```bash
pip install -r requirements.txt
python3 fetch_nifty_expiry_cas.py     # or fetch_sensex_expiry_cas.py -> expiry_data/
python3 fetch_nifty_daily_1min.py     # or fetch_sensex_daily_1min.py -> 1min_download/
```

For a specific already-listed expiry: `python3 fetch_nifty_expiry_cas.py 2026-09-22`.
For a specific earlier day this front week: `python3 fetch_nifty_daily_1min.py 2026-09-16`.

## Command reference

Run from `~/Trading/download free data`.

### Manual fetch — expiry_data/ (bypasses the "is today the expiry" check)

```bash
python3 fetch_nifty_expiry_cas.py                            # today, if it's a listed NIFTY expiry
python3 fetch_sensex_expiry_cas.py                            # today, if it's a listed SENSEX expiry
python3 fetch_nifty_expiry_cas.py 2026-09-22                   # an explicit, still-listed expiry date
python3 collage_atm_cas.py "expiry_data/2026-09-22/NIFTY"      # rebuild the collage for a folder already pulled
```

### Manual fetch — 1min_download/ (any trading day, not just expiry)

```bash
python3 fetch_nifty_daily_1min.py                  # today's front-week NIFTY chain
python3 fetch_sensex_daily_1min.py                  # today's front-week SENSEX chain
python3 fetch_nifty_daily_1min.py 2026-09-16         # a specific earlier day this front week
```

### Local macOS scheduler (launchd, Mon-Fri 15:45)

```bash
./setup_scheduler.sh status       # is it loaded?
./setup_scheduler.sh install      # load both jobs (persists across reboot/login)
./setup_scheduler.sh uninstall    # unload both jobs
./setup_scheduler.sh run-now      # trigger both immediately, for testing
tail -f logs/nifty_pull.log logs/sensex_pull.log   # watch the last local run
```

### Cloud scheduler (GitHub Actions — `gh` CLI, needs `gh auth login` once)

```bash
gh workflow list                                    # confirm both workflows are active
gh workflow run fetch-nifty-expiry.yml               # trigger a run now, instead of waiting for cron
gh workflow run fetch-sensex-expiry.yml
gh run list --workflow=fetch-nifty-expiry.yml --limit 5   # recent run history + pass/fail
gh run view <run-id> --log                           # full log of one run
gh run view <run-id> --log-failed                     # just the failed step's log
```

### Sync your local clone with whatever the cloud job committed

```bash
git pull origin main
```

### Check what actually ran, without opening GitHub

```bash
git log --oneline -10                     # commit history (cloud + local runs both land here)
git log --oneline --author="github-actions"   # only the automated commits
```
