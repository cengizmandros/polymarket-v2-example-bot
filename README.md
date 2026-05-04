# polymarket-v2-example-bot

> A minimal, well-commented Python reference for placing orders on Polymarket's CLOB V2 — no SDK dependency.

Polymarket's V2 exchange launches **April 22, 2026**. This repo shows the full V2 order flow from first principles: building the struct, signing EIP-712, submitting to the REST API, and wrapping USDC to pUSD for collateral. All without the official `py-clob-client-v2` package — just `eth-account`, `httpx`, and `web3`.

Pair this with [polymarket-v2-migration-kit](https://github.com/cengizmandros/polymarket-v2-migration-kit) to audit your existing V1 bot.

## Why no SDK

Building against the raw API teaches you what the SDK does under the hood. When something goes wrong at 3am during the cutover, you'll know where to look.

Also: the SDK lags the API in practice. If Polymarket ships a contract change, raw code catches up first.

## What's inside

```
polymarket-v2-example-bot/
├── src/
│   ├── constants.py    # V2 addresses, domain versions, chain IDs
│   ├── order.py        # V2 Order struct + builders (BUY / SELL)
│   ├── signer.py       # EIP-712 signing for Order + ClobAuth
│   ├── client.py       # REST client (HMAC L2 auth)
│   └── collateral.py   # USDC → pUSD wrap via CollateralOnramp
├── examples/
│   ├── inspect_orderbook.py  # Public — no creds needed
│   ├── place_order.py        # Build, sign, submit a limit BUY
│   └── wrap_collateral.py    # 3-tx on-chain wrap flow
├── .env.example
└── requirements.txt
```

## Installation

```bash
git clone https://github.com/cengizmandros/polymarket-v2-example-bot.git
cd polymarket-v2-example-bot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# fill in POLY_FUNDER, POLY_PRIVATE_KEY, and derived API creds
```

## Quickstart

### Inspect an orderbook (no creds required)

```bash
python examples/inspect_orderbook.py
```

Pulls the best 10 bid/ask levels from `/book` and prints them in a table. Works against staging (`clob-v2.polymarket.com`) or production.

### Place a limit order

```bash
python examples/place_order.py
```

Builds a V2 Order struct, signs it with your wallet, and submits via REST. Reads all credentials from `.env`.

### Wrap USDC → pUSD

```bash
python examples/wrap_collateral.py 10   # wrap $10 of USDC into pUSD
```

Executes the full 3-transaction flow:
1. Approve USDC to the Collateral Onramp
2. Call `wrap(amount)` — burns USDC, mints pUSD
3. Approve pUSD to the V2 exchange

> ⚠️ The Collateral Onramp address isn't public as of this writing. Fill it into `src/constants.py` once Polymarket publishes it.

## Key V2 patterns, demonstrated

### EIP-712 domains — the #1 pitfall

```python
# Exchange domain — V2 bumps version to "2"
V2_EXCHANGE_DOMAIN_VERSION = "2"

# ClobAuthDomain — STAYS at "1" even in V2. Easy to conflate.
CLOB_AUTH_DOMAIN_VERSION = "1"
```

Both fields are literally called `version`. Mix them up and every signed order fails with a cryptic "invalid signature" error. See `src/signer.py::assert_versions_correct()` — bake this into your tests.

### Order struct — removed fields are GONE

```python
# V1 had these. In V2 they're removed entirely:
#   nonce, expiration, taker, feeRateBps

# V2 adds:
#   timestamp (ms, replaces nonce for uniqueness)
#   metadata (bytes32, application-defined)
#   builder  (bytes32, for builder attribution)
```

See `src/order.py::V2Order`. Includes builders for both BUY and SELL sides, with proper 6-decimal USDC unit scaling.

### Fees — protocol-controlled, not embedded

V1 embedded `feeRateBps` in the signed order. V2 removes this entirely — the protocol sets fees at match time:

```
fee = C × feeRate × p × (1 − p)
```

Makers never pay fees. Only takers. To fetch current per-market fee params, call `getClobMarketInfo(conditionId)` and read `fd.rate`.

### pUSD collateral

V2 replaces USDC.e (bridged) with pUSD (Polymarket's own ERC-20, 1:1 backed by USDC via the Collateral Onramp). polymarket.com handles this for you. API traders must do it themselves:

```python
# in src/collateral.py
wrap_usdc_to_pusd(
    web3=web3,
    wallet_address=wallet,
    private_key=private_key,
    amount_usdc_units=to_usdc_units(100),   # wrap $100
    ...
)
```

### HMAC L2 auth — unchanged in V2

The REST API auth flow is the same. See `src/client.py::_l2_headers()`. The headers you need per request:

```
POLY_ADDRESS, POLY_TIMESTAMP, POLY_API_KEY, POLY_PASSPHRASE, POLY_SIGNATURE
```

The `POLY_BUILDER_*` HMAC headers from V1 are **gone**. Builder attribution moves into the signed `builder` field of the Order struct.

## Testing against staging

```bash
# In .env:
CLOB_HOST=https://clob-v2.polymarket.com
```

The staging environment is open to everyone for testing pre-cutover. Your regular API credentials work against it.

## V2 toolkit

This bot is part of a V2 toolkit you can use end-to-end:

1. **[polymarket-v2-migration-kit](https://github.com/cengizmandros/polymarket-v2-migration-kit)** — audit your existing V1 codebase
2. **polymarket-v2-example-bot** — this repo, the reference implementation
3. **[polymarket-cheatsheet](https://github.com/cengizmandros/polymarket-cheatsheet)** — single-page V2 API reference
4. **[polymarket-backtest](https://github.com/cengizmandros/polymarket-backtest)** — event-driven V2-aware backtest framework

## Caveats

- The official V2 SDK (`py-clob-client-v2`) is now published — this repo intentionally goes without it so you understand the wire protocol. Use the SDK for production trading; come here when something breaks.
- Verify the Collateral Onramp + pUSD contract addresses against the latest published artifacts; structural code is in place.
- ABIs for the Collateral Onramp in `src/collateral.py` are minimal — verify against published artifacts once available.

## License

MIT — use at your own risk, always test against staging before cutover, do not YOLO real funds without dry-runs.

## Contributing

Found a bug or want to add an example (cancellation, TIF orders, neg-risk markets)? PRs welcome. Keep additions didactic — clarity beats cleverness.
