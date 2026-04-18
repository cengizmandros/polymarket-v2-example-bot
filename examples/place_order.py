"""Example: build, sign, and submit a V2 limit buy order.

Prerequisites:
  - .env with POLY_API_KEY / SECRET / PASSPHRASE / FUNDER / PRIVATE_KEY
  - Your wallet has pUSD allowance approved to the V2 exchange
  - A valid token_id (fetch one from the Polymarket Gamma API)

Usage:
    python examples/place_order.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console

from src.client import CLOBClient
from src.constants import V2_STAGING_CLOB
from src.order import build_limit_buy
from src.signer import assert_versions_correct, sign_order

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
console = Console()


async def main() -> None:
    # Runtime sanity — ensure constants are set correctly
    assert_versions_correct()

    funder = os.getenv("POLY_FUNDER", "").strip()
    private_key = os.getenv("POLY_PRIVATE_KEY", "").strip()
    api_key = os.getenv("POLY_API_KEY", "").strip()
    api_secret = os.getenv("POLY_API_SECRET", "").strip()
    api_passphrase = os.getenv("POLY_API_PASSPHRASE", "").strip()
    clob_host = os.getenv("CLOB_HOST", V2_STAGING_CLOB).strip()

    if not all([funder, private_key, api_key, api_secret, api_passphrase]):
        console.print("[red]Missing credentials in .env[/]")
        return

    # ── Replace this with a real token_id from Gamma API ──
    # Find one via: https://gamma-api.polymarket.com/events?active=true&tag_slug=soccer
    # The clobTokenIds field gives you YES and NO token IDs per market.
    token_id = int(
        "4394372887385518214471608448209527405727552777602031099972143344338178308080"
    )  # Example: Spain to win 2026 World Cup YES

    console.print("[bold cyan]V2 Limit Buy Example[/]\n")
    console.print(f"  Host:   {clob_host}")
    console.print(f"  Funder: {funder}")
    console.print(f"  Token:  {str(token_id)[:30]}...\n")

    # 1. Build the order
    order = build_limit_buy(
        token_id=token_id,
        price=0.05,          # try to buy at 5¢
        amount_usd=5.0,       # spend $5 → 100 shares @ 5¢
        maker=funder,
    )
    console.print(f"[green]Built order:[/]")
    console.print(f"  salt:          {order.salt}")
    console.print(f"  timestamp:     {order.timestamp}")
    console.print(f"  makerAmount:   {order.makerAmount} ({order.makerAmount / 1e6} USDC)")
    console.print(f"  takerAmount:   {order.takerAmount} ({order.takerAmount / 1e6} shares)")
    console.print(f"  side:          BUY")
    console.print(f"  sigType:       EOA\n")

    # 2. Sign it (V2 Exchange domain, version "2")
    signature = sign_order(order, private_key=private_key, neg_risk=False)
    console.print(f"[green]Signed:[/] {signature[:20]}...\n")

    # 3. Submit via REST
    client = CLOBClient(
        host=clob_host,
        funder_address=funder,
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase,
    )
    try:
        resp = await client.post_order(order.to_api_dict(signature))
        console.print(f"[bold green]✓ Order placed:[/] {resp}")
    except Exception as exc:
        console.print(f"[red]✗ Order rejected:[/] {exc}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
