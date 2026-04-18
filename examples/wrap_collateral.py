"""Example: wrap USDC.e → pUSD via Collateral Onramp.

This is a V2-specific flow. API-only traders need to do this themselves;
polymarket.com users get it handled automatically.

⚠️ SENDS 3 ON-CHAIN TRANSACTIONS and costs gas. Test with a small amount
first, ideally against a Polygon fork.

Usage:
    python examples/wrap_collateral.py <amount_usdc>
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console

from src.collateral import check_exchange_allowance, check_pusd_balance, wrap_usdc_to_pusd
from src.constants import (
    COLLATERAL_ONRAMP_ADDRESS,
    PUSD_ADDRESS,
    USDC_POLYGON_ADDRESS,
    V2_STANDARD_EXCHANGE,
)
from src.order import to_usdc_units

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
console = Console()


def main() -> None:
    if PUSD_ADDRESS is None or COLLATERAL_ONRAMP_ADDRESS is None:
        console.print(
            "[red]pUSD and Collateral Onramp addresses not yet published by "
            "Polymarket as of this writing.[/]\n"
            "[yellow]This example is structurally ready. Fill in the addresses "
            "in src/constants.py once they're announced in docs.[/]"
        )
        return

    try:
        from web3 import Web3
    except ImportError:
        console.print("[red]Install web3: pip install web3[/]")
        return

    rpc = os.getenv("POLYGON_RPC", "https://polygon-rpc.com").strip()
    wallet = os.getenv("POLY_FUNDER", "").strip()
    private_key = os.getenv("POLY_PRIVATE_KEY", "").strip()

    if not wallet or not private_key:
        console.print("[red]Missing POLY_FUNDER or POLY_PRIVATE_KEY in .env[/]")
        return

    amount_usd = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    amount_units = to_usdc_units(amount_usd)

    console.print(f"[bold cyan]USDC → pUSD wrap[/]\n")
    console.print(f"  Wallet:       {wallet}")
    console.print(f"  RPC:          {rpc}")
    console.print(f"  Amount:       ${amount_usd} ({amount_units} units)\n")

    web3 = Web3(Web3.HTTPProvider(rpc))
    if not web3.is_connected():
        console.print("[red]Could not connect to Polygon RPC[/]")
        return

    # Check pre-state
    pusd_before = check_pusd_balance(web3, PUSD_ADDRESS, wallet) / 1e6
    allow_before = check_exchange_allowance(
        web3, PUSD_ADDRESS, wallet, V2_STANDARD_EXCHANGE,
    ) / 1e6

    console.print(f"  pUSD balance before: {pusd_before:.2f}")
    console.print(f"  exchange allowance:  {allow_before:.2f}\n")

    confirm = input("Proceed with 3 on-chain transactions? [y/N] ")
    if confirm.strip().lower() != "y":
        console.print("[dim]Cancelled.[/]")
        return

    tx_hashes = wrap_usdc_to_pusd(
        web3,
        wallet_address=wallet,
        private_key=private_key,
        usdc_address=USDC_POLYGON_ADDRESS,
        pusd_address=PUSD_ADDRESS,
        onramp_address=COLLATERAL_ONRAMP_ADDRESS,
        exchange_address=V2_STANDARD_EXCHANGE,
        amount_usdc_units=amount_units,
    )

    console.print("\n[green]All transactions confirmed:[/]")
    for i, h in enumerate(tx_hashes, 1):
        console.print(f"  {i}. {h}")

    pusd_after = check_pusd_balance(web3, PUSD_ADDRESS, wallet) / 1e6
    console.print(f"\n  pUSD balance after: [bold green]{pusd_after:.2f}[/]")


if __name__ == "__main__":
    main()
