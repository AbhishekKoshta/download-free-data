"""NIFTY daily 1-min front-week option-chain archive (NSE).

Runs on EVERY trading day (not just expiry day) so intraday option data
survives past that week's expiry - Upstox's free API drops a contract from
its master the moment it expires, so anything not captured before then is
gone for good. This builds a running historical archive for algo backtesting.

Usage:
    python3 fetch_nifty_daily_1min.py               # today
    python3 fetch_nifty_daily_1min.py 2026-09-16     # a specific day this front week

See cas_expiry_common.py for the shared logic and the free-API coverage limits.
"""
from cas_expiry_common import SymbolConfig, main_cli_daily

CONFIG = SymbolConfig(
    label="NIFTY",
    master_url="https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz",
    option_name="NIFTY",
    index_key="NSE_INDEX|Nifty 50",
    strike_step=50,
    strike_band=150,
)

if __name__ == "__main__":
    main_cli_daily(CONFIG)
