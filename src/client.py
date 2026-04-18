"""Minimal REST client for Polymarket CLOB V2 — no SDK dependency.

Why build this from scratch when py-clob-client-v2 exists?
- Educational: shows what the SDK does under the hood
- Future-proof: works even if SDK lags behind API changes
- Small surface area: easier to audit/debug
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class CLOBClient:
    """Thin wrapper around the Polymarket CLOB V2 REST API."""

    def __init__(
        self,
        *,
        host: str,
        funder_address: str,
        api_key: str,
        api_secret: str,
        api_passphrase: str,
    ):
        self.host = host.rstrip("/")
        self.funder = funder_address.lower()
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase

        # Use one persistent AsyncClient for connection pooling
        self._http = httpx.AsyncClient(
            base_url=self.host,
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._http.aclose()

    # ── HMAC L2 auth ────────────────────────────────────────────────────────

    def _l2_headers(
        self, *, method: str, path: str, body: str = "",
    ) -> dict[str, str]:
        """Build L2 (HMAC) auth headers for an API call.

        Same flow as V1 — L2 auth is unchanged in V2.
        """
        timestamp = str(int(time.time()))
        prehash = timestamp + method.upper() + path + body
        secret = self.api_secret.encode("utf-8")
        mac = hmac.new(secret, prehash.encode("utf-8"), hashlib.sha256)
        signature = mac.digest().hex()

        return {
            "POLY_ADDRESS": self.funder,
            "POLY_TIMESTAMP": timestamp,
            "POLY_API_KEY": self.api_key,
            "POLY_PASSPHRASE": self.api_passphrase,
            "POLY_SIGNATURE": signature,
            "Content-Type": "application/json",
        }

    # ── Public endpoints (no auth needed) ──────────────────────────────────

    async def get_orderbook(self, token_id: str) -> dict:
        """Fetch the full orderbook for a CLOB token."""
        resp = await self._http.get("/book", params={"token_id": token_id})
        resp.raise_for_status()
        return resp.json()

    async def get_midpoint(self, token_id: str) -> float:
        """Fetch the mid-price for a CLOB token."""
        resp = await self._http.get("/midpoint", params={"token_id": token_id})
        resp.raise_for_status()
        return float(resp.json().get("mid", 0))

    async def get_price(self, token_id: str, side: str) -> float:
        """Fetch best buy (BUY) or sell (SELL) price for a token."""
        resp = await self._http.get(
            "/price", params={"token_id": token_id, "side": side.upper()},
        )
        resp.raise_for_status()
        return float(resp.json().get("price", 0))

    async def get_clob_market_info(self, condition_id: str) -> dict:
        """V2: fetch per-market CLOB parameters.

        Returns a dict with:
          - mts: minimum tick size
          - mos: minimum order size
          - fd:  fee details (rate, exponent, takerOnly flag)
          - t:   token list with outcomes
          - rfqe: RFQ enabled flag
        """
        resp = await self._http.get(
            "/markets/{}/clob".format(condition_id),
        )
        resp.raise_for_status()
        return resp.json()

    # ── Authenticated endpoints ────────────────────────────────────────────

    async def post_order(self, order_body: dict) -> dict:
        """POST /order — submit a signed V2 order."""
        path = "/order"
        body = json.dumps(order_body, separators=(",", ":"))
        headers = self._l2_headers(method="POST", path=path, body=body)
        resp = await self._http.post(path, headers=headers, content=body)
        if resp.status_code >= 400:
            logger.warning("post_order failed %d: %s", resp.status_code, resp.text[:300])
        resp.raise_for_status()
        return resp.json()

    async def cancel_order(self, order_id: str) -> dict:
        """DELETE /order/{id} — cancel an open order."""
        path = f"/order/{order_id}"
        headers = self._l2_headers(method="DELETE", path=path)
        resp = await self._http.request("DELETE", path, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def get_open_orders(self) -> list[dict]:
        """GET /orders — list my open orders."""
        path = "/orders"
        headers = self._l2_headers(method="GET", path=path)
        resp = await self._http.get(path, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def get_balance_allowance(self, asset_type: str = "COLLATERAL") -> dict:
        """GET /balance-allowance — query your on-chain balance + approval.

        In V2, `asset_type=COLLATERAL` returns your pUSD balance + approval to
        the V2 exchange. Use this to detect whether you need to wrap more USDC.
        """
        path = "/balance-allowance"
        headers = self._l2_headers(method="GET", path=path)
        resp = await self._http.get(
            path, headers=headers, params={"asset_type": asset_type},
        )
        resp.raise_for_status()
        return resp.json()
