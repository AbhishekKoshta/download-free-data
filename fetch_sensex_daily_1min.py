"""SENSEX daily 1-min front-week option-chain archive (BSE).

Runs on EVERY trading day (not just expiry day) so intraday option data
survives past that week's expiry - Upstox's free API drops a contract from
its master the moment it expires, so anything not captured before then is
gone for good. This builds a running historical archive for algo backtesting.

Usage:
    python3 fetch_sensex_daily_1min.py               # today
    python3 fetch_sensex_daily_1min.py 2026-09-16     # a specific day this front week

See cas_expiry_common.py for the shared logic and the free-API coverage limits.
"""
from cas_expiry_common import SymbolConfig, main_cli_daily

CONFIG = SymbolConfig(
    label="SENSEX",
    master_url="https://assets.upstox.com/market-quote/instruments/exchange/BSE.json.gz",
    option_name="SENSEX",
    index_key="BSE_INDEX|SENSEX",
    strike_step=100,
    strike_band=300,
)

if __name__ == "__main__":
    main_cli_daily(CONFIG)
