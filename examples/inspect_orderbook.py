"""Example: fetch and pretty-print the orderbook for a token.

This one needs no credentials — purely read-only public data.

Usage:
    python examples/inspect_orderbook.py <token_id>
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from src.client import CLOBClient
from src.constants import V2_STAGING_CLOB

load_dotenv()
console = Console()


async def main() -> None:
    token_id = sys.argv[1] if len(sys.argv) > 1 else (
        "4394372887385518214471608448209527405727552777602031099972143344338178308080"
    )
    clob_host = os.getenv("CLOB_HOST", V2_STAGING_CLOB).strip()

    # For public endpoints we can pass dummy API creds — they're unused
    client = CLOBClient(
        host=clob_host,
        funder_address="0x0000000000000000000000000000000000000000",
        api_key="", api_secret="", api_passphrase="",
    )

    try:
        book = await client.get_orderbook(token_id)
        bids = book.get("bids", [])
        asks = book.get("asks", [])

        # Polymarket CLOB: bids ASC (best = last), asks DESC (best = last)
        best_bid = float(bids[-1]["price"]) if bids else 0
        best_ask = float(asks[-1]["price"]) if asks else 0
        mid = (best_bid + best_ask) / 2 if bids and asks else None

        console.print(f"\n[bold cyan]Orderbook for token {str(token_id)[:20]}...[/]\n")
        console.print(f"  Best bid:  [green]{best_bid:.3f}[/]")
        console.print(f"  Best ask:  [red]{best_ask:.3f}[/]")
        if mid:
            console.print(f"  Midpoint:  [bold]{mid:.3f}[/]")
        console.print()

        t = Table(show_header=True, header_style="bold")
        t.add_column("Bid size", justify="right")
        t.add_column("Bid price", justify="right", style="green")
        t.add_column("Ask price", justify="right", style="red")
        t.add_column("Ask size", justify="right")

        # Top 10 levels each side
        top_bids = list(reversed(bids[-10:])) if bids else []
        top_asks = list(reversed(asks[-10:])) if asks else []
        rows = max(len(top_bids), len(top_asks))

        for i in range(rows):
            bid = top_bids[i] if i < len(top_bids) else {"price": "", "size": ""}
            ask = top_asks[i] if i < len(top_asks) else {"price": "", "size": ""}
            t.add_row(
                str(bid.get("size", "")),
                str(bid.get("price", "")),
                str(ask.get("price", "")),
                str(ask.get("size", "")),
            )

        console.print(t)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
