"""NIFTY expiry-day CAS data puller (NSE, Tuesday weekly expiry).

Usage:
    python3 fetch_nifty_expiry_cas.py               # nearest listed expiry
    python3 fetch_nifty_expiry_cas.py 2026-09-22     # a specific listed expiry

See cas_expiry_common.py for the shared logic and the free-API coverage limits.
"""
from cas_expiry_common import SymbolConfig, main_cli

CONFIG = SymbolConfig(
    label="NIFTY",
    master_url="https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz",
    option_name="NIFTY",
    index_key="NSE_INDEX|Nifty 50",
    strike_step=50,
    strike_band=150,
)

if __name__ == "__main__":
    main_cli(CONFIG)
