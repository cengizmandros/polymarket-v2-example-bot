"""Polymarket CLOB V2 constants — addresses, domain versions, chain IDs.

All values sourced from https://docs.polymarket.com/v2-migration
(as of April 2026, V2 cutover April 22).
"""

from __future__ import annotations

# ── Chain ───────────────────────────────────────────────────────────────────

POLYGON_CHAIN_ID = 137


# ── Exchange contracts (V2) ─────────────────────────────────────────────────

# Standard markets (2-outcome YES/NO)
V2_STANDARD_EXCHANGE = "0xE111180000d2663C0091e4f400237545B87B996B"

# NegRisk markets (multi-outcome grouped, mutually exclusive)
V2_NEG_RISK_EXCHANGE = "0xe2222d279d744050d28e00520010520000310F59"


# ── EIP-712 Exchange domain ─────────────────────────────────────────────────

# IMPORTANT: Exchange domain version BUMPED from "1" to "2" in V2
V2_EXCHANGE_DOMAIN_NAME = "Polymarket CTF Exchange"
V2_EXCHANGE_DOMAIN_VERSION = "2"   # <-- V2

V2_NEG_RISK_EXCHANGE_DOMAIN_NAME = "Polymarket Neg Risk CTF Exchange"
V2_NEG_RISK_DOMAIN_VERSION = "2"   # <-- V2


# ── EIP-712 Auth domain (L1 API auth — UNCHANGED in V2) ─────────────────────

# Do NOT bump this to "2" — V2 keeps auth at "1"
CLOB_AUTH_DOMAIN_NAME = "ClobAuthDomain"
CLOB_AUTH_DOMAIN_VERSION = "1"   # <-- STAYS at 1 in V2


# ── Collateral ──────────────────────────────────────────────────────────────

# pUSD is the new V2 collateral token (backed by USDC via CollateralOnramp)
# Placeholder addresses — replace with official V2 addresses from docs
# when you build in production (as of this writing they are not public yet)
PUSD_ADDRESS = None  # TODO: set after Polymarket publishes
COLLATERAL_ONRAMP_ADDRESS = None  # TODO: set after Polymarket publishes

# USDC.e on Polygon (for reference/wrap source)
USDC_POLYGON_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"


# ── CLOB API endpoints ──────────────────────────────────────────────────────

V2_STAGING_CLOB = "https://clob-v2.polymarket.com"
PRODUCTION_CLOB = "https://clob.polymarket.com"   # V2 post-April-22
GAMMA_API = "https://gamma-api.polymarket.com"     # unchanged
DATA_API = "https://data-api.polymarket.com"       # unchanged


# ── Order sides ─────────────────────────────────────────────────────────────

SIDE_BUY = 0
SIDE_SELL = 1


# ── Signature types ────────────────────────────────────────────────────────

# 0 = EOA (direct wallet signs)
# 1 = POLY_PROXY (proxy signs for a Gnosis Safe)
# 2 = POLY_GNOSIS_SAFE
SIG_TYPE_EOA = 0
SIG_TYPE_POLY_PROXY = 1
SIG_TYPE_POLY_GNOSIS_SAFE = 2


# ── Zero values (convenience) ───────────────────────────────────────────────

ZERO_BYTES32 = "0x" + "00" * 32
ZERO_ADDRESS = "0x" + "00" * 20
