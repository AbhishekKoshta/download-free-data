"""SENSEX expiry-day CAS data puller (BSE, Thursday weekly expiry).

Usage:
    python3 fetch_sensex_expiry_cas.py               # nearest listed expiry
    python3 fetch_sensex_expiry_cas.py 2026-09-24     # a specific listed expiry

See cas_expiry_common.py for the shared logic and the free-API coverage limits.
"""
from cas_expiry_common import SymbolConfig, main_cli

CONFIG = SymbolConfig(
    label="SENSEX",
    master_url="https://assets.upstox.com/market-quote/instruments/exchange/BSE.json.gz",
    option_name="SENSEX",
    index_key="BSE_INDEX|SENSEX",
    strike_step=100,
    strike_band=300,
)

if __name__ == "__main__":
    main_cli(CONFIG)
